import collections

# Integrated fix for Python 3.10+ compatibility
if not hasattr(collections, 'MutableMapping'):
    import collections.abc
    collections.MutableMapping = collections.abc.MutableMapping
    collections.Sequence = collections.abc.Sequence
    collections.Callable = collections.abc.Callable
    collections.Set = collections.abc.Set
    collections.Iterable = collections.abc.Iterable
    collections.Mapping = collections.abc.Mapping

# Now your Ryu imports can follow
from ryu.base import app_manager
# ... the rest of your code

from ryu.base import app_manager
from ryu.controller import ofp_event
from ryu.controller.handler import CONFIG_DISPATCHER, MAIN_DISPATCHER, set_ev_cls
from ryu.ofproto import ofproto_v1_3
from ryu.lib.packet import packet, ethernet

BLOCKED_MAC = "00:00:00:00:00:03"  # H3 is blocked

class LearningSwitch(app_manager.RyuApp):

    OFP_VERSIONS = [ofproto_v1_3.OFP_VERSION]

    def __init__(self, *args, **kwargs):
        super(LearningSwitch, self).__init__(*args, **kwargs)
        self.mac_table = {}

    @set_ev_cls(ofp_event.EventOFPSwitchFeatures, CONFIG_DISPATCHER)
    def switch_connect_handler(self, ev):
        datapath = ev.msg.datapath
        ofproto  = datapath.ofproto
        parser   = datapath.ofproto_parser

        match   = parser.OFPMatch()
        actions = [parser.OFPActionOutput(ofproto.OFPP_CONTROLLER,
                                          ofproto.OFPCML_NO_BUFFER)]
        self.install_flow(datapath, priority=0, match=match, actions=actions)

    @set_ev_cls(ofp_event.EventOFPPacketIn, MAIN_DISPATCHER)
    def packet_in_handler(self, ev):
        msg      = ev.msg
        datapath = msg.datapath
        ofproto  = datapath.ofproto
        parser   = datapath.ofproto_parser
        in_port  = msg.match['in_port']

        pkt = packet.Packet(msg.data)
        eth = pkt.get_protocols(ethernet.ethernet)[0]
        src_mac = eth.src
        dst_mac = eth.dst

        dpid = datapath.id
        self.logger.info("PacketIn sw=%s in_port=%s src=%s dst=%s",
                         dpid, in_port, src_mac, dst_mac)

        # Scenario 2 — blocked host
        if src_mac == BLOCKED_MAC:
            self.logger.info("BLOCKED %s — installing drop rule", src_mac)
            match = parser.OFPMatch(eth_src=BLOCKED_MAC)
            self.install_flow(datapath, priority=10, match=match, actions=[])
            return

        # Scenario 1 — normal learning
        self.mac_table[src_mac] = in_port

        if dst_mac in self.mac_table:
            out_port = self.mac_table[dst_mac]
            match    = parser.OFPMatch(in_port=in_port, eth_dst=dst_mac)
            actions  = [parser.OFPActionOutput(out_port)]
            self.install_flow(datapath, priority=1, match=match, actions=actions)
            self.logger.info("UNICAST %s → port %s  (flow installed)", dst_mac, out_port)
        else:
            out_port = ofproto.OFPP_FLOOD
            self.logger.info("FLOOD — %s unknown", dst_mac)

        actions = [parser.OFPActionOutput(out_port)]
        out = parser.OFPPacketOut(
            datapath=datapath,
            buffer_id=msg.buffer_id,
            in_port=in_port,
            actions=actions,
            data=msg.data
        )
        datapath.send_msg(out)

    def install_flow(self, datapath, priority, match, actions):
        parser = datapath.ofproto_parser
        inst   = [parser.OFPInstructionActions(
                      datapath.ofproto.OFPIT_APPLY_ACTIONS, actions)]
        mod = parser.OFPFlowMod(
            datapath=datapath,
            priority=priority,
            match=match,
            instructions=inst
        )
        datapath.send_msg(mod)