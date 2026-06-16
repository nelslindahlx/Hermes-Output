import os, sys, filecmp
sys.path.insert(0, '/Users/nelslindahl')

from captain_fractal_studio import HardwareAuth, FastStegoEngine

seed = HardwareAuth.get_machine_fingerprint()
key_path = '/Users/nelslindahl/key_2_dictionary_test.json'
engine = FastStegoEngine(key_2_path=key_path)
engine.generate_dictionary(seed)

inp = '/Users/nelslindahl/captain_fractal_studio.py'
zip_out = '/tmp/test_roundtrip.captain.zip'
restored = '/tmp/test_roundtrip_RESTORED'

for p in [zip_out, restored]:
    if os.path.exists(p):
        os.remove(p)

res = engine.encrypt_and_package(inp, seed)
assert res == zip_out, res
assert os.path.exists(zip_out), zip_out

out = engine.decrypt_and_extract(zip_out, seed)
assert out == restored, out
assert os.path.exists(restored), restored

assert filecmp.cmp(inp, restored, shallow=False)
print('roundtrip_ok')
