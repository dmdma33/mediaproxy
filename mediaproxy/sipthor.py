#
# Copyright (C) 2008 AG Projects
# Author: Ruud Klaver <ruud@ag-projects.com>
#

from twisted.internet import reactor

from application import log
from application.configuration import *
from application.system import default_host_ip
from application.process import process

from gnutls.constants import *

from thor.entities import ThorEntities, GenericThorEntity
from thor.eventservice import EventServiceClient, ThorEvent
from thor.tls import X509Credentials

from mediaproxy import configuration_filename

class ThorNetworkConfig(ConfigSection):
    domain = "sipthor.net"
    nodeIP = default_host_ip
    multiply = 1000

configuration = ConfigFile(configuration_filename)
configuration.read_settings("ThorNetwork", ThorNetworkConfig)

class SIPThorMediaRelayBase(EventServiceClient):
    topics = ["Thor.Members"]
    
    def __init__(self):
        self.node = GenericThorEntity(ThorNetworkConfig.nodeIP, ["media_relay"])
        self.presence_message = ThorEvent('Thor.Presence', self.node.id)
        self.shutdown_message = ThorEvent('Thor.Leave', self.node.id)
        credentials = X509Credentials(cert_name='node')
        credentials.session_params.compressions = (COMP_LZO, COMP_DEFLATE, COMP_NULL)
        EventServiceClient.__init__(self, ThorNetworkConfig.domain, credentials)

    def handle_event(self, event):
        sip_proxy_ips = [node.ip for node in ThorEntities(event.message, role="sip_proxy")]
        self.update_dispatchers(sip_proxy_ips)

    def update_dispatchers(self, dispatchers):
        raise NotImplementedError()

    def _handle_SIGHUP(self, *args):
        log.msg("Received SIGHUP, shutting down after all sessions have expired.")
        reactor.callFromThread(self.shutdown, False)

    def _handle_SIGINT(self, *args):
        if process._daemon:
            log.msg("Received SIGINT, shutting down.")
        else:
            log.msg("Received KeyboardInterrupt, exiting.")
        reactor.callFromThread(self.shutdown, True)

    def _handle_SIGTERM(self, *args):
        log.msg("Received SIGTERM, shutting down.")
        reactor.callFromThread(self.shutdown, True)

    def shutdown(self, kill_sessions):
        raise NotImplementedError()