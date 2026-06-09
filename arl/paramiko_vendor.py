# paramiko_vendor.py -- paramiko implementation of the dulwich SSHVendor interface
#
# Vendored from dulwich.contrib.paramiko_vendor (Copyright (C) 2013 Aaron
# O'Mullan <aaron.omullan@friendco.de>), which was dual-licensed under the
# Apache License, Version 2.0 and the GNU General Public License v2.0 or later.
#
# dulwich dropped the contrib/ package from its distribution as of 0.25.0, so
# this adapter is maintained here. It lets dulwich authenticate over SSH using
# an in-memory paramiko private key (paramiko is already a dependency of this
# project), which the SSH vendors dulwich still ships (subprocess ssh, plink)
# cannot do.

"""Paramiko-backed SSH vendor for dulwich.

Install it by overriding ``dulwich.client.get_ssh_vendor``::

    from dulwich import client as _mod_client
    from arl.paramiko_vendor import ParamikoSSHVendor
    _mod_client.get_ssh_vendor = lambda: ParamikoSSHVendor(pkey=pkey)
"""

import paramiko
import paramiko.client


class _ParamikoWrapper:
    def __init__(self, client, channel) -> None:
        self.client = client
        self.channel = channel

        # Channel must block
        self.channel.setblocking(True)

    @property
    def stderr(self):
        return self.channel.makefile_stderr("rb")

    def can_read(self):
        return self.channel.recv_ready()

    def write(self, data):
        return self.channel.sendall(data)

    def read(self, n=None):
        data = self.channel.recv(n)
        data_len = len(data)

        # Closed socket
        if not data:
            return b""

        # Read more if needed
        if n and data_len < n:
            diff_len = n - data_len
            return data + self.read(diff_len)
        return data

    def close(self) -> None:
        self.channel.close()


class ParamikoSSHVendor:
    # http://docs.paramiko.org/en/2.4/api/client.html

    def __init__(self, **kwargs) -> None:
        self.kwargs = kwargs

    def run_command(
        self,
        host,
        command,
        username=None,
        port=None,
        password=None,
        pkey=None,
        key_filename=None,
        ssh_command=None,
        protocol_version=None,
        **kwargs,
    ):
        # ssh_command is part of dulwich's SSHVendor.run_command interface but
        # is meaningless for a paramiko connection; accept and ignore it so it
        # is never forwarded into paramiko's connect().
        client = paramiko.SSHClient()

        connection_kwargs = {"hostname": host}
        connection_kwargs.update(self.kwargs)
        if username:
            connection_kwargs["username"] = username
        if port:
            connection_kwargs["port"] = port
        if password:
            connection_kwargs["password"] = password
        if pkey:
            connection_kwargs["pkey"] = pkey
        if key_filename:
            connection_kwargs["key_filename"] = key_filename
        connection_kwargs.update(kwargs)

        policy = paramiko.client.MissingHostKeyPolicy()
        client.set_missing_host_key_policy(policy)
        client.connect(**connection_kwargs)

        # Open SSH session
        channel = client.get_transport().open_session()

        if protocol_version is None or protocol_version == 2:
            channel.set_environment_variable(name="GIT_PROTOCOL", value="version=2")

        # Run commands
        channel.exec_command(command)

        return _ParamikoWrapper(client, channel)
