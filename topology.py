from mininet.net import Mininet
from mininet.node import RemoteController
from mininet.topo import Topo
from mininet.log import setLogLevel
from mininet.cli import CLI

class SingleSwitchTopo(Topo):
    def build(self):
        switch = self.addSwitch('s1')

        h1 = self.addHost('h1', mac='00:00:00:00:00:01', ip='10.0.0.1/24')
        h2 = self.addHost('h2', mac='00:00:00:00:00:02', ip='10.0.0.2/24')
        h3 = self.addHost('h3', mac='00:00:00:00:00:03', ip='10.0.0.3/24')

        self.addLink(h1, switch)
        self.addLink(h2, switch)
        self.addLink(h3, switch)

def run():
    topo = SingleSwitchTopo()

    net = Mininet(
        topo=topo,
        controller=RemoteController('c0', ip='127.0.0.1', port=6653)
    )

    net.start()

    print("\n--- Network started ---")
    print("H1: 10.0.0.1  mac=00:00:00:00:00:01  port=1")
    print("H2: 10.0.0.2  mac=00:00:00:00:00:02  port=2")
    print("H3: 10.0.0.3  mac=00:00:00:00:00:03  port=3  (BLOCKED)")
    print("\nType 'exit' to stop the network")
    print("-------------------------------\n")

    CLI(net)

    net.stop()

if __name__ == '__main__':
    setLogLevel('info')
    run()