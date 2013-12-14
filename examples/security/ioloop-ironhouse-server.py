#!/usr/bin/env python

'''
Ironhouse extends Stonehouse with client public key authentication. 

This is the strongest security model we have today, protecting against every
attack we know about, except end-point attacks (where an attacker plants 
spyware on a machine to capture data before it's encrypted, or after it's 
decrypted).

This example demonstrates the IOLoopAuthenticator
'''

import datetime
import os
import sys
import time
import zmq
import zmq.auth
from zmq.eventloop import ioloop, zmqstream


class IronhouseServer(object):
    ''' Ironhouse Server '''

    def __init__(self, context, server_cert_file, endpoint='tcp://*:9000'):
        self.context = context
        self.endpoint = endpoint
        self.socket = None
        self.stream = None
        self.send_timer = None
        self.public, self.secret = zmq.auth.load_certificate(server_cert_file)

    def start(self):
        self.socket = self.context.socket(zmq.ROUTER)
        self.socket.curve_secretKey = self.secret
        self.socket.curve_publicKey = self.public
        self.socket.curve_server = True  # must come before bind
        self.stream = zmqstream.ZMQStream(self.socket, ioloop.IOLoop.instance())
        self.stream.on_recv(self.on_message)
        self.stream.on_send(self.on_sent)
        self.stream.bind('tcp://*:9000')

    def stop(self):
        if self.send_timer:
            self.send_timer.stop()
        self.stream.close()

    def on_message(self, frames):
        ''' '''
        print "received request"
        identity = frames[0]
        now = datetime.datetime.now()
        msg = [identity, str(now)]
        print "sending reply"
        self.stream.send_multipart(msg)

    def on_sent(self, msg, status):
        # Shutdown after sending reply msg message
        ioloop.IOLoop.instance().add_timeout(0.1, ioloop.IOLoop.instance().stop)


if __name__ == '__main__':

    verbose = False
    if '-v' in sys.argv:
        verbose = True

    if verbose:
        import logging
        logging.basicConfig(format='%(asctime)-15s %(levelname)s %(message)s', 
                            level=logging.DEBUG)

    # These direcotries are generated by the generate_keys script
    base_dir = os.path.dirname(__file__)
    keys_dir = os.path.join(base_dir, 'certificates')
    public_keys_dir = os.path.join(base_dir, 'public_keys')
    secret_keys_dir = os.path.join(base_dir, 'private_keys')

    if not (os.path.exists(keys_dir) and os.path.exists(keys_dir) and os.path.exists(keys_dir)):
        print "Certificates are missing - run generate_certificates script first"
        sys.exit(1)

    ctx = zmq.Context().instance()

    # Start an authenticator for this context.
    auth = zmq.auth.IOLoopAuthenticator(ctx, verbose=verbose)
    auth.start()
    auth.allow('127.0.0.1')
    # Tell authenticator to use the certificate in a directory
    auth.configure_curve(domain='*', location=public_keys_dir)

    server_cert_file = os.path.join(secret_keys_dir, "server.key_secret")
    iron_server = IronhouseServer(ctx, server_cert_file)
    iron_server.start()

    try:
        ioloop.IOLoop.instance().start()
    except KeyboardInterrupt:
        pass

    # stop auth thread
    auth.stop()
