from twisted.internet import reactor, threads, protocol
from twisted.internet.task import LoopingCall
from twisted.internet.endpoints import TCP4ClientEndpoint, connectProtocol
from twisted.internet.protocol import Protocol, Factory, ClientFactory
from twisted.python import log
from collections import defaultdict
import sys


class EventProtocol(Protocol):
    def dataReceived(self, data):
        """ split along delimiter (\n), chomp trailing newline as unused, grab
            event id before storing away so we can put these in order.
        """
        message = data.rstrip()
        for event in message.split(delimiter):
            sequence = int(event.split(separator)[0])
            self.factory.events[sequence] = event
            log.msg("storing event %s" % event)


class EventFactory(Factory):
    protocol = EventProtocol

    def __init__(self, userFactory):
        self.currEvent = 1
        self.events = {}
        self.users = userFactory.users
        self.followers = defaultdict(list)

    def nextEvent(self):
        """ Return the next event in sequence or else
            return a signal that it's not ready yet
        """
        if self.currEvent in self.events:
            return self.events[self.currEvent]
        else:
            return -1

    def eventDispatcher(self):
        """ take the sequence number, pull up the event if available, determine
            msg type and arguments, route message, update followers, notify, &c
        """
        event = self.nextEvent()
        if event < 0:
            return
        else:
            log.msg("processing event: %s" % event)
            fields = event.split(separator)
            try:
                sequence = int(fields[0])
            except:
                return

            try:
                msgType = fields[1]
            except:
                return

            fromId = int(fields[2]) if len(fields) >= 3 else None
            toId = int(fields[3]) if len(fields) >= 4 else None
            self.currEvent += 1

            if msgType == 'F':
                self.followers[toId].append(fromId)
                if toId in self.users:
                    self.users[toId].transport.write(event + '\n')
                    log.msg("%d following %d" % (fromId, toId))
            elif msgType == 'U':
                if fromId in self.followers[toId]:
                    self.followers[toId].remove(fromId)
                    log.msg("%d unfollowing %d" % (fromId, toId))
            elif msgType == 'B':
                for user in self.users:
                    user.transport.write(event + '\n')
                    log.msg("broadcasting %s to %s" % (event, user))
            elif msgType == 'P':
                if toId in self.users:
                    self.users[toId].transport.write(event + '\n')
                    log.msg("%s sending private message to %s" % (fromId, toId))
            elif msgType == 'S':
                for follower in self.followers[fromId]:
                    if follower in self.users:
                        self.users[follower].transport.write(event + '\n')
                        log.msg("sending status %s to user %s" %
                                (event, self.users[follower]))

class UserProtocol(Protocol):
    def connectionMade(self):
        try:
            self.transport.setTcpKeepAlive(1)
        except AttributeError: pass

    def dataReceived(self, data):
        """ the only data we'll receive from user should be userId
        """
        userId = int(data.strip(delimiter))
        self.factory.users[userId] = self
        log.msg("registering user: {%s: %s}" %
                 (userId, self.factory.users[userId]))


class UserFactory(Factory):
    protocol = UserProtocol

    def __init__(self):
        self.nextEvent = 1
        self.users = {}
        self.followers = {}


if __name__ == '__main__':
    delimiter = '\n'
    separator = '|'

    """ send the user factory instance to the event factory constructor
        then the events loops will have access to all: users, followers, events
    """
    userClientsFactory = UserFactory()
    eventSourceFactory = EventFactory(userClientsFactory)

    log.startLogging(sys.stdout)

    reactor.listenTCP(9099, userClientsFactory)
    reactor.listenTCP(9090, eventSourceFactory)

    try:
        LoopingCall(eventSourceFactory.eventDispatcher).start(0.00001)
    except Exception as err:
        print "ERROR starting looping call: %s" % err

    reactor.run()
