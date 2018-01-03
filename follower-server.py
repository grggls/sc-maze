from twisted.internet import reactor, threads, protocol
from twisted.internet.task import LoopingCall
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.internet.protocol import Protocol, Factory, ClientFactory
from twisted.python import log
import sys


class EventFactory(protocol.ClientFactory):
    def __init__(self):
        self.nextEvent = 1

    def buildProtocol(self, addr):
        p = EventProtocol()
        p.factory = self
        return p


class EventProtocol(Protocol):
    def dataReceived(self, data):
        # split along delimiter (\n), chomp trailing newline as unused, grab event id
        # before storing away so we can put these in order. ensure we have utf8
        message = data.rstrip()
        for event in message.split(delimiter):
            log.msg("%s received" % event)
            sequence = event.split(separator)[0]
            try:
                events[int(sequence)] = event
                log.msg("events: %s" % events)
            except:
                pass    # bad event?


class UserProtocol(Protocol):
    def connectionMade(self):
        try:
            self.transport.setTcpKeepAlive(1)
        except AttributeError: pass

    # only data received from user should be userId
    def dataReceived(self, data):
        userId = data.strip(delimiter)
        users[int(userId)] = self
        followers[int(userId)] = []


def eventDispatcher(events, nextEvent):
    if nextEvent in events:
        fields = events[nextEvent].split(separator)
        sequence = int(fields[0])
        msgType = fields[1]
        fromId = int(fields[2]) if len(fields) > 2 else None
        toId = int(fields[3]) if len(fields) > 3 else None

        log.msg("processing: %s" % events[nextEvent])
        nextEvent += 1

        if msgType == 'F':
            followers[toId].append(fromId)
            users[toId].transport.write(message)
            log.msg("%s to follow %s" % fromId, toId)
        elif msgType == 'U':
            if fromId in followers[toId]:
                followers[toId].remove(fromId)
                log.msg("%s to unfollow %s" % toId, fromId)
        elif msgType == 'B':
            for user in users:
                user.transport.write(message)
                log.msg("broadcasting %s to %s" % message, user)
        elif msgType == 'P':
            users[toId].transport.write(message)
            log.msg("%s sending private message to %s" % fromId, toId)
        elif msgType == 'S':
            if followers[fromId]:
                for follower in followers[fromId]:
                    users[follower].transport.write(message)
                    log.msg("sending status %s to user %s" % message, users[follower])


if __name__ == '__main__':
    events = {}     # store all events here, keep full string, key is sequence #
    users = {}      # store all UserProtocol objects here, to write to later
    followers = {}  # key is userID, value is list of followers {1: [3, 7], 2: [9]...}

    delimiter = '\n'
    separator = '|'

    nextEvent = 1   # just a dumb counter

    eventSourceFactory = EventFactory()
    eventSourceFactory.protocol = EventProtocol

    userClientsFactory = Factory()
    userClientsFactory.protocol = UserProtocol
    userClientsFactory.clients = []

    log.startLogging(sys.stdout)

    try:
        LoopingCall(eventDispatcher, events, nextEvent).start(0.0001)
    except Exception as err:
        print "ERROR starting looping call: %s" % err

    reactor.listenTCP(9090, eventSourceFactory)
    reactor.listenTCP(9099, userClientsFactory)
    reactor.run()

