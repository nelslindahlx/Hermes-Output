import os, sys, filecmp
sys.path.insert(0, "/Users/nelslindahl/Hermes-Output/captain-fractal-studio")

from captain_fractal_studio import HardwareAuth, FastStegoEngine

seed = HardwareAuth.get_machine_fingerprint()
key_path = "/Users/nelslindahl/Hermes-Output/captain-fractal-studio/key_2_dictionary_test.json"
engine = FastStegoEngine(key_2_path=key_path)
engine.generate_dictionary(seed)

inp = "/Users/nelslindahl/Hermes-Output/captain-fractal-studio/captain_fractal_studio.py"
zip_out = "/tmp/test_roundtrip.captain.zip"
restored = "/tmp/test_roundtrip_RESTORED"

for p in [zip_out, restored]:
    if os.path.exists(p):
        os.remove(p)

res = engine.encrypt_and_package(inp, seed, output_path=zip_out)
assert res == zip_out and os.path.exists(zip_out), (res, zip_out)

out = engine.decrypt_and_extract(zip_out, seed, output_path=restored)
assert out == restored and os.path.exists(restored), (out, restored)

assert filecmp.cmp(inp, restored, shallow=False)
print("roundtrip_ok")
