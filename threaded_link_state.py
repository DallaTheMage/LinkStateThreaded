'''
    Autore: Lorenzo Dall'Ara
    Matricola: 0001068964
    Versione di Python: 3.13.1
'''
from threaded_routing import ThreadRouter, Network

if __name__ == "__main__":
    # Rete - Dizionario di adiacenza, le distanze sono None perché verranno generate random all'interno della classe Network.
    network_dictionary:dict = {
        "A": {"D":None, "B":None, "E":None},
        "B": {"A":None, "C":None, "E":None},
        "C": {"B":None, "E":None, "H":None},
        "D": {"E":None, "A":None},
        "E": {"A":None, "B":None, "C":None, "D":None, "F":None,"H":None},
        "F": {"E":None, "G":None},
        "G": {"F":None, "H":None},
        "H": {"G":None, "E":None, "C":None}
    }

    network = Network(network=network_dictionary)
    network_routers = {name: ThreadRouter(name, network) for name in network_dictionary}

    for router_name in network_dictionary:
        neighbors_names = network_dictionary[router_name]
        for neighbor_name in neighbors_names:
            network_routers[router_name].add_neighbor(neighbor=network_routers[neighbor_name])

    for router in network_routers.values():
        router.start()

    for router in network_routers.values():
        router.join()

