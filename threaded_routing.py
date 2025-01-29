'''
    Autore: Lorenzo Dall'Ara
    Matricola: 0001068964
    Versione di Python: 3.13.1
'''
from threading import Thread, Condition
import random
import heapq

class ThreadRouter(Thread):
    def __init__(self, name, network):
        super(ThreadRouter, self).__init__()
        self.name:str = name                                          # Nome del router.
        self.network:Network = network                                # Rete in cui il router effettua lo scambio di pacchetti.
        self.topology_manager:TopologyManager = TopologyManager(name) # Manager che si occupa di gestire la topologia in maniera thread-safe.
        self.neighbor_manager:NeighborManager = NeighborManager(name) # Manager che si occupa di gestire la lista dei vicini in maniera thread-safe
        self.packet_manager:PacketManager = PacketManager(self)       # Manager che si occupa di gestire la generazione e la gestione dei pacchetti in maniera thread-safe.

    def add_neighbor(self, neighbor:'ThreadRouter' = None) -> None:
        self.neighbor_manager.add_new_neighbor(neighbor=neighbor)
        topology_update = { self.name : { neighbor.name : None } }
        if self.topology_manager.update_topology(received_topology=topology_update):
            print(f"\nRouter {self.name} ha mappato il nuovo vicino {neighbor.name} all'interno della topologia.")
        else:
            print(f"\nRouter {self.name} non è stato in grado di mappare il nuovo vicino {neighbor.name} all'interno della topologia.")

    def send_hello(self) -> dict:
        packet:dict = self.packet_manager.generate_simple_packet()
        print(f"\nRouter {self.name} invia pacchetto Hello a {','.join(self.neighbor_manager.read_neighbors_names())}")
        for neighbor in self.neighbor_manager.read_neighbors():
            if not self.network.transmit_hello(hello_packet=packet, target=neighbor):
                print(f"\nRouter {self.name} rimuove {neighbor.name} dalla lista dei vicini perché non più raggiungibile e aggiorna la topologia.")
                topology_update = {self.name: {neighbor.name: None}}
                self.topology_manager.update_topology(received_topology=topology_update)
                self.neighbor_manager.remove_unreachable_neighbor(neighbor)

    def receive_hello(self, packet:dict[str, 'ThreadRouter']) -> bool:
        try:
            neighbors_names = self.neighbor_manager.read_neighbors_names()
            if packet['source'].name in neighbors_names:
                print(f"\nRouter {self.name} ha ricevuto pacchetto Hello da {packet['source'].name}")
            else:
                print(f"\nRouter {self.name} ha ricevuto pacchetto Hello da vicino sconosciuto {packet['source'].name}")
                print(f"\nRouter {self.name} aggiunge {packet['source'].name} alla lista dei vicini.")
                self.add_neighbor(packet['source'])
            return True
        except Exception as exception:
            print(f"\nRouter {self.name} ha ricevuto pacchetto Hello corrotto: {exception}")
            return False

    def send_echo(self) -> None:
        # Ottieni la topologia correlata al router di destinazione
        route: dict = self.topology_manager.read_subtopology(self.name)
        packet:dict = self.packet_manager.generate_simple_packet()
        for target_router in self.neighbor_manager.read_neighbors():
            # Controlla se il target_router è già presente nella topologia del router corrente
            if route is None or route.get(target_router.name) is None:
                print(f"\nRouter {self.name} invia Echo Packet a {target_router.name}")
                # Invia il pacchetto Echo e ricevi la risposta
                distance = self.network.transmit_echo(echo_packet=packet, target=target_router)
                # Aggiungi il risultato nella topologia
                topology_update = {self.name: {target_router.name: distance}}
                if self.topology_manager.update_topology(received_topology=topology_update):
                    print(f"\nRouter {self.name} aggiorna topologia inerente a router {target_router.name} con valore: {distance}")
                else:
                    print(f"\nRouter {self.name} non è stato in grado di aggiornare la topologia inerente al router {target_router.name} con valore: {distance}")
            else:
                print(f"\nRouter {self.name} si rifiuta di inviare Echo Packet a {target_router.name} perché ha già una distanza conosciuta.")


    def receive_echo(self, packet:dict[str, 'ThreadRouter'], distance_from:int) -> bool:
        try:
            topology_update = {self.name: {packet['source'].name: distance_from}}
            print(f"\nRouter {self.name} riceve Echo Packet da {packet['source'].name}")
            print(f"\nRouter {self.name} risponde a Echo Packet da {packet['source'].name}")
            if self.topology_manager.update_topology(received_topology=topology_update):
                print(f"\nRouter {self.name} aggiorna topologia inerente a router {packet['source'].name} con valore: {distance_from}")
            else:
                print(f"\nRouter {self.name} non è stato in grado di aggiornare la topologia inerente al router {packet['source'].name} con valore: {distance_from}")
            return True
        except Exception as exception:
            print(f"\nRouter {self.name} riceve Echo Packet corrotto da {packet['source'].name}: ", exception)
            return False

    def start_LSU_flooding(self):
        # Avvia la procedura di flooding a tutti i vicini
        print(f"\nRouter {self.name} invia LSU a {','.join(self.neighbor_manager.read_neighbors_names())}.")
        self.network.execute_LSU_flooding(source=self, lsu_packet=self.packet_manager.generate_LSU(self.topology_manager.read_topology()), neighbors=self.neighbor_manager.read_neighbors())

    def receive_LSU(self, lsu_packet:dict[str, dict]):
        # Decrementa il TTL del pacchetto LSU
        lsu_packet['TTL'] = lsu_packet['TTL'] - 1
        # Verifica se il TTL è maggiore di 0
        if lsu_packet['TTL'] > 0:
            # Verifica se il pacchetto LSU è già stato ricevuto
            if not self.packet_manager.is_old_lsu(lsu_id=lsu_packet.get('ID')):
                self.packet_manager.collect_old_lsu(lsu_id=lsu_packet.get('ID'))
                # Se la topologia è stata aggiornata correttamente, esegui il flooding
                if self.topology_manager.update_topology(received_topology=lsu_packet['topology']):
                    print(f"\nRouter {self.name} ha ricevuto un LSU da {lsu_packet['router_name']} e ha aggiornato la topologia.")
                    print(f"\nRouter {self.name} ricalcola la propria tabella di routing.")
                    self.topology_manager.generate_routing_table()
                    self.network.execute_LSU_flooding(source=self, lsu_packet=lsu_packet, neighbors=self.neighbor_manager.read_neighbors())
            else:
                print(f"\nRouter {self.name} ignora tentativo di flood LSU perché il pacchetto {lsu_packet['ID']} è già stato ricevuto in precedenza.")
        else:
            print(f"\nRouter {self.name} ignora tentativo di flood LSU perché il pacchetto {lsu_packet['ID']} ha terminato il suo TTL.")


    # Trasmette LSR ai vicini
    def send_LSR(self, neighbor:'ThreadRouter', route_key:str):
        packet:dict = self.packet_manager.generate_LSR(route_key)
        for neighbor in self.neighbor_manager.read_neighbors():
            print(f"\nRouter {self.name} invia LSR a {neighbor.name}")
            response = self.network.transmit_LSR(target=neighbor, lsr_packet=packet)
            if response is not None:
                topology_update = {response['response_for']: response['topology']}
                self.topology_manager.update_topology(received_topology=topology_update)
                break

    # Riceve LSR packet e soddisfa la richiesta se possiede informazioni a riguardo.
    def receive_LSR(self, packet) -> dict | None:
        route:dict = self.topology_manager.read_topology().get(packet['request_for'])
        if route is not None:
            # Rispondi con un LSU che contiene la topologia richiesta
            lsr_response = {
                'ID': f"{self.name}-{str(self.packet_manager.read_sequence_number())}",
                'router_name': self.name,
                'response_for': packet['request_for'],
                'topology': route
            }
            self.packet_manager.increase_sequence_number()
            print(f"\nRouter {self.name} risponde a LSR da {packet['router_name']}")
            return lsr_response
        else:
            return None

    def run(self):
        print(f"\nRouter {self.name} avvia la fase di Hello.")
        self.send_hello()
        print(f"\nRouter {self.name} avvia la fase di Echo.")
        self.send_echo()
        print(f"\nRouter {self.name} avvia la fase di LSU flooding.")
        self.start_LSU_flooding()
        print(f"\nRouter {self.name} avvia simulazione LSR.")
        self.send_LSR(random.choice(self.neighbor_manager.read_neighbors()), random.choice(list(self.topology_manager.read_topology().keys())))
        self.topology_manager.sort_topology()
        self.topology_manager.print_routing_table()

class TopologyManager:
    def __init__(self, router_name:str):
        self.owner_name:str = router_name                            # Nome del router di cui il manager sta gestendo la topologia
        self.topology:dict[str, dict[str, int]] = {router_name : {}} # Topologia conosciuta dal router (link e costi).
        self.routing_table:dict = {}                                 # Tabella di routing (nome router: distanza minima).
        self.next_hop_table:dict = {}                                # Tabella dei next hop.
        self.topology_condition:Condition = Condition()              # Condition variable per gestione concorrenza su topologia
        self.reading_topology:bool = False
        self.updating_topology:bool = False

    def format_subtopology(self, table):
        return f"{table}"

    def from_topology_to_list(self):
        return list(map(self.format_subtopology, self.read_topology().items()))

    def sort_topology(self) -> None:
            with self.topology_condition:
                while self.updating_topology or self.reading_topology:
                    self.topology_condition.wait()
                self.updating_topology = True
                keys:list = list(self.topology.keys())
                keys.sort()
                self.topology = {key: self.topology[key] for key in keys}
                self.updating_topology = False
                self.topology_condition.notify_all()

    def update_topology(self, received_topology: dict[str, dict[str, int]]) -> bool:
            try:
                with self.topology_condition:
                    while self.updating_topology or self.reading_topology:
                        self.topology_condition.wait()
                    self.updating_topology = True
                    for key, table in received_topology.items():
                        if key not in self.topology:
                            self.topology[key] = table
                        else:
                            self.topology.get(key).update(table)
                    self.updating_topology = False
                    self.topology_condition.notify_all()
                return True
            except Exception:
                return False

    def read_subtopology(self, key:str) -> dict[str, int]:
        with self.topology_condition:
            while self.updating_topology:
                self.topology_condition.wait()
            self.reading_topology = True
            actual_topology = self.topology.get(key)
            self.reading_topology = False
            self.topology_condition.notify_all()
        return actual_topology

    def read_topology(self) -> dict[str, dict[str, int]]:
        with self.topology_condition:
            while self.updating_topology:
                self.topology_condition.wait()
            self.reading_topology = True
            actual_topology = self.topology
            self.reading_topology = False
            self.topology_condition.notify_all()
        return actual_topology

    def print_routing_table(self) -> None:
        distances, next_hops = self.generate_routing_table()
        print(
            f"\nRouter {self.owner_name} ha terminato di calcolare la propria tabella di routing.\n",
            f"Topologia Router {self.owner_name}:\n{"\n".join(self.from_topology_to_list())}\n",
            f"Tabella di routing per il router {self.owner_name}:\n{distances}\n",
            f"Tabella dei next hop per il router {self.owner_name} (destinazione: prossimo router da attraversare):\n{next_hops}\n"
        )

    def generate_routing_table(self) -> tuple[dict[str, int], dict[str, str]]:
        actual_topology = self.read_topology()
        print(actual_topology)
        # Inizializzazione dizionario per memorizzare le distanze per tabella di routing
        distances = {router: float('inf') for router in actual_topology}
        # Inizializzazione dizionario per memorizzare i nextHop
        next_hop = {router: None for router in actual_topology}
        distances[self.owner_name] = 0
        queue = [(0, self.owner_name)]
        while queue:
            current_distance, current_router = heapq.heappop(queue)
            # Se la distanza corrente è maggiore della distanza registrata, saltala
            if current_distance > distances.get(current_router, 0):
                continue
            # Esplora i vicini
            actual_neighbors = actual_topology.get(current_router, {})
            for neighbor, cost in actual_neighbors.items():
                distance = round(current_distance + cost, 5)
                # Se la nuova distanza è minore di quella già registrata
                if distance < distances.get(neighbor, float('inf')):
                    distances[neighbor] = distance   # Aggiorna la distanza
                    if(current_router == self.owner_name):
                        next_hop[neighbor] = neighbor # Aggiorna il nextHop con il vicino
                    else:
                        next_hop[neighbor] = current_router # Aggiorna il nextHop con router
                    heapq.heappush(queue, (distance, neighbor))
        # Imposta la tabella di routing come un dizionario di distanze.
        self.routing_table = distances
        # Imposta dizionario dei nextHop
        self.next_hop_table = next_hop
        # Restituisce sia le distanze che il nextHop
        return (distances, next_hop)

class NeighborManager:
    def __init__(self, router_name:str):
        self.owner_name:str = router_name
        self.neighbors:list["ThreadRouter"] = []         # Lista dei vicini del router.
        self.neighbors_condition:Condition = Condition() # Condition variable per gestione concorrenza sui vicini
        self.reading_neighbors:bool = False
        self.updating_neighbors:bool = False

    def add_new_neighbor(self, neighbor:ThreadRouter) -> None:
        if (neighbor is not None) and (neighbor.name != self.owner_name):
            with self.neighbors_condition:
                while self.updating_neighbors or self.reading_neighbors:
                    self.neighbors_condition.wait()
                self.updating_neighbors = True
                self.neighbors.append(neighbor)
                self.updating_neighbors = False
                self.neighbors_condition.notify_all()

    def remove_unreachable_neighbor(self, neighbor:"ThreadRouter") -> None:
        if neighbor is not None:
            with self.neighbors_condition:
                while self.updating_neighbors or self.reading_neighbors:
                    self.neighbors_condition.wait()
                self.updating_neighbors = True
                self.neighbors.remove(neighbor)
                self.updating_neighbors = False
                self.neighbors_condition.notify_all()

    def get_neighbor_name(self, neighbor:"ThreadRouter") -> str:
        return neighbor.name

    def read_neighbors_names(self) -> list:
        with self.neighbors_condition:
            while self.updating_neighbors:
                self.neighbors_condition.wait()
            self.reading_neighbors = True
            neighbors_names:list = map(self.get_neighbor_name, self.neighbors)
            self.reading_neighbors = False
            self.neighbors_condition.notify_all()
        return neighbors_names

    def read_neighbors(self) -> list["ThreadRouter"]:
        with self.neighbors_condition:
            while self.updating_neighbors:
                self.neighbors_condition.wait()
            self.reading_neighbors = True
            neighbors = self.neighbors
            self.reading_neighbors = False
            self.neighbors_condition.notify_all()
        return neighbors

class PacketManager:
    PACKET_TTL:int = 15
    def __init__(self, owner:"ThreadRouter"):
        self.owner = owner
        self.lsu_sequence_number:int = 0          # Numero di sequenza dei pacchetti LSU generati da questo router.
        self.old_lsus:set[str] = set()            # LSU già ritrasmessi e/o ricevuti per evitare ridondanze.

        self.lsu_condition:Condition = Condition()
        self.reading_lsu:bool = False
        self.updating_lsu:bool = False

        self.number_condition:Condition = Condition()
        self.reading_number:bool = False
        self.updating_number:bool = False

    def increase_sequence_number(self):
        with self.number_condition:
            while self.reading_number or self.updating_number:
                self.number_condition.wait()
            self.updating_number = True
            self.lsu_sequence_number += 1
            self.updating_number = False
            self.number_condition.notify_all()

    def read_sequence_number(self) -> int:
        with self.number_condition:
            while self.updating_number:
                self.number_condition.wait()
            self.reading_number_number = True
            number = self.lsu_sequence_number
            self.reading_number = False
            self.number_condition.notify_all()
        return number

    def generate_simple_packet(self) -> dict:
        return {'source': self.owner}

    def generate_LSU(self, topology:dict[str, dict[str, int]]):
        # Genera un pacchetto LSU con la mappa della topologia
        lsu_packet = {
            'ID': f"{self.owner.name}-{str(self.read_sequence_number())}",
            'router_name': self.owner.name,
            'topology': topology,
            'TTL': self.PACKET_TTL
        }
        self.increase_sequence_number()
        return lsu_packet

    # Genera un pacchetto LSR per richiedere informazioni sulla topologia
    def generate_LSR(self, damaged_route:str):
        return {'router_name': self.owner.name, 'request_for': damaged_route}

    def is_old_lsu(self, lsu_id:str) -> bool:
        with self.lsu_condition:
            while self.updating_lsu:
                self.lsu_condition.wait()
            self.reading_lsu = True
            is_old = ( lsu_id in self.old_lsus )
            self.reading_lsu = False
            self.lsu_condition.notify_all()
        return is_old

    def collect_old_lsu(self, lsu_id:str) -> bool:
        with self.lsu_condition:
            while self.updating_lsu or self.reading_lsu:
                self.lsu_condition.wait()
            self.updating_lsu = True
            self.old_lsus.add(lsu_id)
            self.updating_lsu = False
            self.lsu_condition.notify_all()

class Network:
    MAX_DISTANCE:int = 12
    MIN_DISTANCE:int = 1

    def __init__(self, network:dict[str, dict[str, int]]={}):
        self.network = network
        for route_table in self.network.values():
            for name in route_table:
                distance = random.randint(self.MIN_DISTANCE, self.MAX_DISTANCE)
                route_table.update({name:distance})

    def transmit_hello(self, hello_packet:dict={'source':None}, target:"ThreadRouter"=None) -> bool:
        if target is not None:
            print(f"\nNetwork transmission: hello packet da {hello_packet['source'].name} viene inviato a {target.name}")
            response = target.receive_hello(packet=hello_packet)
            print(f"\nNetwork transmission: {response} viene inviato a {hello_packet['source'].name}")
            return response
        else:
            return False

    def find_distance(self, source:"ThreadRouter", target:"ThreadRouter") -> int:
        return (self.network.get(source.name)).get(target.name)

    def transmit_echo(self, echo_packet:dict, target:"ThreadRouter") -> int | None:
        distance = self.find_distance(echo_packet['source'], target)
        print(f"\nNetwork transmission: echo packet da {echo_packet['source'].name} viene inviato a {target.name}")
        if target.receive_echo(packet=echo_packet, distance_from=distance):
            print(f"\nNetwork transmission: {distance} viene inviato a {echo_packet['source'].name}")
            return distance
        else:
            print(f"\nNetwork transmission: None viene inviato a {echo_packet['source'].name}")
            return None

    def transmit_LSR(self, target:"ThreadRouter", lsr_packet:dict):
        print(f"\nNetwork transmission: LSR = {lsr_packet} viene inviato a {target.name}")
        response = target.receive_LSR(packet=lsr_packet)
        print(f"\nNetwork transmission: {target.name} invia LSR Response = {response} viene inviato a {lsr_packet['router_name']}")
        return response

    def execute_LSU_flooding(self, source:"ThreadRouter",lsu_packet:dict, neighbors:list["ThreadRouter"]):
        for neighbor in neighbors:
            print(f"\nNetwork transmission: Router {source.name} invia LSU a {neighbor.name}.")
            neighbor.receive_LSU(lsu_packet)