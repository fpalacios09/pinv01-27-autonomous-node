# Raspberry Pi 4G Router Integration

The PINV01-27 autonomous node uses a Raspberry Pi with a 4G modem to provide internet connectivity to the NVIDIA Jetson.

The complete Raspberry Pi setup is maintained in a separate repository:

- [Raspberry Pi 4G Router](https://github.com/fpalacios09/raspberry-4g-router)

## Role in the PINV01-27 architecture

The Raspberry Pi acts as the internet gateway for the Jetson. Its main responsibilities are:

- Establishing the 4G connection through the cellular modem.
- Sharing the internet connection with the Jetson.
- Providing connectivity for IPFS update downloads.
- Allowing the Jetson to remain independent from a permanent wired network.

## Recommended integration sequence

1. Configure and validate the Raspberry Pi router by following the instructions in the dedicated repository.
2. Connect the Raspberry Pi and Jetson through the selected network interface.
3. Verify that the Jetson receives an IP address.
4. Confirm internet connectivity from the Jetson:

```bash
ping -c 4 1.1.1.1
```

5. Confirm DNS resolution:

```bash
ping -c 4 github.com
```

6. Verify IPFS connectivity:

```bash
ipfs swarm peers
```

7. Test access to an IPFS object:

```bash
ipfs cat <CID>
```

## Validation criteria

The router integration is considered operational when:

- The Jetson has an IP address.
- The Jetson can reach the internet.
- DNS resolution works.
- The IPFS daemon can connect to peers.
- The update manager can download and verify an update package.

## Related repository

Repository URL:

```text
https://github.com/fpalacios09/raspberry-4g-router
```
