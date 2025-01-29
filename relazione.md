### **Documentazione del progetto Python: Gestione della rete tramite Link State Routing (Hello, Echo, LSU, LSR)**

#### **Introduzione**

Questo progetto implementa, utilizzando **Python 3.13.1**, una simulazione di routing in una rete usando il protocollo Link State Routing (LSR) con gestione concorrente tramite thread. Ogni router agisce come un thread separato che comunica con gli altri router per costruire e aggiornare la propria topologia di rete e la tabella di routing.

Il progetto si compone di due file principali:

1. **`threaded_link_state.py`**: Imposta la rete, inizializza e avvia i router.
2. **`threaded_routing.py`**: Contiene la logica di funzionamento dei router e della gestione della concorrenza relativa ai pacchetti, alla topologia, ai vicini e della sincronizzazione tramite Condition variable.

---

### **1. `threaded_link_state.py`**

#### **Funzione principale**

Questo script definisce la rete, inizializza i router e avvia i relativi thread di gestione per ciascun router nella rete.
I router utilizzano i metodi del modulo `threaded_routing.py` per scambiare pacchetti di tipo Hello, Echo, LSU, e LSR per aggiornare e mantenere la topologia della rete.

- **Dizionario di rete**: Definisce la topologia della rete come un dizionario di adiacenza, dove i nodi rappresentano i router e le chiavi rappresentano i collegamenti (vicinanza) tra i router.

```python
network_dictionary: dict = {
    "A": {"D": None, "B": None, "E": None},
    "B": {"A": None, "C": None, "E": None},
    # ...
}
```

- **Creazione della rete e dei router**:
  - La rete viene inizializzata tramite la classe `Network`, che viene poi passata ai router definiti dalla classe `ThreadRouter`.
  - Ogni router è rappresentato come un thread, che interagisce con gli altri router tramite la gestione dei vicini e pacchetti di routing.

```python
network_routers = {name: ThreadRouter(name, network) for name in network_dictionary}
```

- **Gestione della topologia e della comunicazione**:
  - Per ogni router, vengono aggiunti i vicini, avviato il relativo thread e vengono eseguiti i metodi per l'invio e la ricezione dei pacchetti.

```python
for router in network_routers.values():
    router.start()

for router in network_routers.values():
    router.join()
```

---

### **2. `threaded_routing.py`**

#### **Classi principali**

1. **`ThreadRouter`**:
   - Rappresenta un router nella rete, gestisce la topologia, i vicini e i pacchetti tramite i manager specifici.
   - Ogni router è un thread che esegue tutte le azioni inerenti a un protocollo Link State per aggiornare la topologia e costruire la tabella di routing.
   - I metodi principali sono:
     - `send_hello()`: Invia pacchetti Hello ai vicini per rilevarli.
     - `send_echo()`: Invia pacchetti Echo per determinare le distanze tra router.
     - `start_LSU_flooding()`: Avvia il flooding LSU per aggiornare la topologia.
     - `send_LSR()`: Invia richieste LSR per ottenere informazioni sulle topologie danneggiate.

2. **`TopologyManager`**:
   - Gestisce la topologia di rete conosciuta da un router.
   - Sincronizza l'accesso alla topologia tramite un oggetto `Condition` per garantire che i thread possano operare in modo thread-safe.
   - I metodi principali includono:
     - `update_topology()`: Aggiorna la topologia del router con nuove informazioni.
     - `read_topology()`: Legge la topologia corrente.
     - `generate_routing_table()`: Genera la tabella di routing utilizzando l'algoritmo di Dijkstra.

3. **`NeighborManager`**:
   - Gestisce la lista dei vicini di ciascun router.
   - I metodi principali sono:
     - `add_new_neighbor()`: Aggiunge un nuovo vicino.
     - `remove_unreachable_neighbor()`: Rimuove i vicini non raggiungibili.
     - `read_neighbors()`: Restituisce la lista dei vicini.
     - `read_neighbors_names()`: Legge i nomi dei vicini.

4. **`PacketManager`**:
   - Gestisce la generazione e la gestione dei pacchetti di routing (Hello, Echo, LSU, LSR).
   - I metodi principali sono:
     - `generate_simple_packet()`: Crea un pacchetto semplice (Hello packet / Echo Packet).
     - `generate_LSU()`: Crea un pacchetto LSU contenente un ID univoco, il nome del router che lo ha generato, la topologia e il TTL.
     - `generate_LSR()`: Crea un pacchetto LSR per chiedere informazioni sulla topologia.

5. **`Network`**:
   - Simula la rete in cui i router comunicano tra loro.
   - Gestisce la trasmissione dei pacchetti (Hello, Echo, LSU, LSR) tra i router.

#### **Funzioni principali**

- **Trasmissione pacchetti**:
  - Ogni tipo di pacchetto (Hello, Echo, LSU, LSR) è inviato ai vicini tramite la rete simulata. La rete trasmette i pacchetti ai router di destinazione e raccoglie le risposte.
  
  ```python
  def transmit_hello(self, hello_packet: dict, target: 'ThreadRouter') -> bool:
      # Logica di trasmissione del pacchetto Hello
  ```

- **Gestione della topologia**:
  - Ogni router mantiene e aggiorna la sua topologia interna, che è sincronizzata con gli altri router tramite pacchetti LSU (Link State Update).
  
  ```python
  def update_topology(self, received_topology: dict[str, dict[str, int]]) -> bool:
      # Logica di aggiornamento della topologia
  ```

- **Generazione delle tabelle di routing**:
  - Una volta che tutti i pacchetti sono stati scambiati, i router calcolano la loro tabella di routing utilizzando l'algoritmo di Dijkstra.

  ```python
  def generate_routing_table(self) -> tuple[dict[str, int], dict[str, str]]:
      # Algoritmo di Dijkstra per la generazione della tabella di routing e dei next hop
  ```

---

### **Esempio di Utilizzo**

Per eseguire la simulazione di routing:

1. Definisci una rete utilizzando un dizionario di adiacenza.
2. Inizializza la rete e i router.
3. Avvia i thread di routing per ciascun router.
4. Ogni router eseguirà autonomamente i vari passaggi di comunicazione e aggiornamento della topologia.
```python
# Esegui lo script
if __name__ == "__main__":
    # Creazione e avvio della rete
    # network_dictionary = { ... }
    network = Network(network_dictionary)
    network_routers = {name: ThreadRouter(name, network) for name in network_dictionary}

    for router in network_routers.values():
        router.start()

    for router in network_routers.values():
        router.join()
```
---

### Problemi Riscontrati
Durante lo sviluppo del progetto, sono emersi alcuni problemi significativi che hanno richiesto soluzioni specifiche o adattamenti del codice.
I principali ostacoli affrontati includono:

1. **Gestione della concorrenza con i thread**:
   - **Descrizione del problema**: Uno dei principali problemi riscontrati è stato la gestione della concorrenza tra i vari thread. Per rendere la simulazione più realistica possibile i router dovevano operare su thread separati, è stato necessario di conseguenza garantire che le operazioni sulla topologia e sulla lista dei vicini fossero sicure e non causassero conflitti o inconsistenze.
   - **Soluzione**: È stata implementata la sincronizzazione utilizzando `Condition` per le variabili condivise, come la topologia e la lista dei vicini, in modo da evitare che più thread potessero modificarle contemporaneamente.

2. **Loop infiniti durante il flooding dei pacchetti LSU**:
   - **Descrizione del problema**: Un altro problema si è verificato durante il flooding dei pacchetti LSU. Senza una contromisura per limitare le ritrasmissioni avremmo potuto incorrere in loop infiniti di ritrasmissione dei pacchetti tra i router.
   - **Soluzione**: È stato introdotto il campo **TTL** nei pacchetti LSU. Ogni volta che un nuovo pacchetto LSU viene ricevuto, il suo TTL viene decrementato. Se il TTL raggiunge zero il pacchetto viene scartato, prevenendo il loop.

3. **Gestione delle informazioni obsolete nei pacchetti LSU**:
   - **Descrizione del problema**: I pacchetti LSU, se non gestiti correttamente, avrebbero potuto portare a problemi di ridondanza nella topologia, inviando più volte gli stessi dati tra i router.
   - **Soluzione**: È stato implementato un meccanismo (una lista) per rilevare i pacchetti LSU già ricevuti e ritrasmessi, evitando il flooding ripetuto e mantenendo la rete più efficiente.

---

### **Conclusioni**
Questo progetto simula il funzionamento di un protocollo di routing Link State all'interno di una rete sfruttando la programmazione concorrente.
La gestione dei pacchetti e la sincronizzazione tra i thread garantisce che la topologia della rete sia aggiornata correttamente in un ambiente concorrente.
I router calcolano autonomamente la loro tabella di routing utilizzando i pacchetti LSU per ottenere e mantenere la visibilità completa sulla rete.

---