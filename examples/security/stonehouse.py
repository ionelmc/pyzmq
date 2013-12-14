#!/usr/bin/env python

'''
Stonehouse uses the "CURVE" security mechanism.

This gives us strong encryption on data, and (as far as we know) unbreakable
authentication. Stonehouse is the minimum you would use over public networks,
and assures clients that they are speaking to an authentic server, while 
allowing any client to connect.
'''

import os
import sys
import time
import zmq
import zmq.auth


def run():
    ''' Run Stonehouse example '''

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
    auth = zmq.auth.ThreadedAuthenticator(ctx)
    auth.start(verbose=True)
    auth.allow('127.0.0.1')
    # Tell the authenticator how to handle CURVE requests
    auth.configure_curve(domain='*', location=zmq.auth.CURVE_ALLOW_ANY)

    server = ctx.socket(zmq.PUSH)
    server_secret_file = os.path.join(secret_keys_dir, "server.key_secret")
    server_public, server_secret = zmq.auth.load_certificate(server_secret_file)
    server.curve_secretKey = server_secret
    server.curve_publicKey = server_public
    server.curve_server = True  # must come before bind
    server.bind('tcp://*:9000')

    client = ctx.socket(zmq.PULL)
    # We need two certificates, one for the client and one for
    # the server. The client must know the server's public key
    # to make a CURVE connection.
    client_secret_file = os.path.join(secret_keys_dir, "client.key_secret")
    client_public, client_secret = zmq.auth.load_certificate(client_secret_file)
    client.curve_secretKey = client_secret
    client.curve_publicKey = client_public

    # The client must know the server's public key to make a CURVE connection.
    server_public_file = os.path.join(public_keys_dir, "server.key")
    server_public, _ = zmq.auth.load_certificate(server_public_file)
    client.curve_serverKey = server_public

    client.connect('tcp://127.0.0.1:9000')

    server.send("Hello")

    poller = zmq.Poller()
    poller.register(client, zmq.POLLIN)
    socks = dict(poller.poll(1000))
    if client in socks and socks[client] == zmq.POLLIN:
        msg = client.recv()
        if msg == "Hello":
            print "Stonehouse test OK"
    else:
        print "Stonehouse test FAIL"

    # stop auth thread
    auth.stop()

if __name__ == '__main__':

    verbose = False
    if '-v' in sys.argv:
        verbose = True

    if verbose:
        import logging
        logging.basicConfig(format='%(asctime)-15s %(levelname)s %(message)s', 
                            level=logging.DEBUG)

    run()
