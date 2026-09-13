import tempfile
import unittest
from pathlib import Path
from twice_monitor.core import Store, Detector, BASE, B58, addresses, beep_sequence
from twice_monitor.service import public_url, retry_delay

ROOT=Path(__file__).resolve().parents[1]
EVM="0x1234567890abcdef1234567890abcdef12345678"
def base58(raw):
    value=int.from_bytes(raw,"big")
    result=""
    while value:
        value, remainder=divmod(value,58)
        result=B58[remainder]+result
    return "1"*(len(raw)-len(raw.lstrip(b"\0")))+result

class DetectionTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.path=Path(self.tmp.name)/"state.db"
        self.store=Store(self.path)
        self.detector=Detector(self.store,ROOT/"research"/"2026-09-13-twice-fun")

    def tearDown(self):
        self.store.close()
        self.tmp.cleanup()

    def test_launcher_true_is_not_enabled(self):
        self.detector.deployment({"enabled":False,"launcherEnabled":True})
        self.assertEqual(self.store.events(),[])

    def test_on_event_and_restart_dedup_and_reenable(self):
        self.detector.deployment({"enabled":False,"launcherEnabled":True})
        self.detector.deployment({"enabled":True,"launcherEnabled":True})
        self.detector.deployment({"enabled":True})
        self.store.close()
        self.store=Store(self.path)
        self.detector=Detector(self.store)
        self.detector.deployment({"enabled":True})
        self.assertEqual(len(self.store.events()),1)
        self.detector.deployment({"enabled":False})
        self.detector.deployment({"enabled":True})
        self.assertEqual(len(self.store.events()),2)

    def test_first_seen_on_alerts(self):
        self.detector.deployment({"enabled":True})
        self.assertEqual(self.store.events()[0]["kind"],"enabled")

    def test_missing_wrong_types_are_errors_not_off(self):
        for payload in ({}, {"enabled":"true"},{"enabled":1},{"enabled":None},[]):
            with self.assertRaises(ValueError):
                self.detector.deployment(payload)
        self.assertIsNone(self.store.get("deployment"))

    def test_saved_real_baseline_has_no_token_alert(self):
        root=ROOT/"research"/"2026-09-13-twice-fun"
        for name in ["api-config.json","app.js","launch-client.js","connection-flow.js","index.html"]:
            self.detector.scan_text((root/name).read_text(encoding="utf-8"),BASE+"/"+name)
        self.assertEqual(self.store.events(),[])

    def test_evm_address_vs_transaction_hash(self):
        self.assertIn(EVM,addresses(EVM))
        self.assertFalse(addresses("0x"+"a"*64))
        self.assertFalse(addresses("foo_"+EVM))
        self.detector.scan_text(EVM,BASE+"/")
        self.detector.scan_text(EVM.upper().replace("0X","0x"),BASE+"/api/tokens")
        self.assertEqual(len(self.store.events()),1)

    def test_solana_must_decode_to_32_bytes(self):
        mint=base58(bytes(range(1,33)))
        self.assertEqual(len(addresses(mint)),1)
        self.assertFalse(addresses("currentAuthorityDerivedKeyBasePubkey"))
        self.assertFalse(addresses(base58(bytes(range(1,31)))))
        self.detector.scan_text(mint,BASE+"/")
        self.assertEqual(self.store.events()[0]["details"]["address"],mint)

    def test_no_real_token_for_empty_filters(self):
        board='<div class="empty-state"><h3>No tokens launched yet.</h3><p>Token deployment available on launch.</p></div>'
        for view in ("all","new","saved"):
            result=self.detector.board(board,"0 tokens listed.",view)
            self.assertEqual(result["count"],0)
        self.assertFalse(self.store.events())

    def test_new_token_without_ca_dedup_across_filters_and_price(self):
        board='<article class="launch-row"><h3>Fixture</h3><div class="row-meta"><span>$FIX</span></div><strong>$69,420</strong><button data-market="fixture-1">View</button></article>'
        self.detector.board(board,"1 token listed.","all")
        self.detector.board(board,"1 token listed.","new")
        self.detector.board(board.replace("$69,420","$80,000"),"1 token listed.","all")
        self.assertEqual(len(self.store.events()),1)
        self.assertEqual(self.store.events()[0]["kind"],"token")

    def test_future_unknown_card_layout_is_not_silent(self):
        self.detector.board('<div class="new-layout">New token $ABC</div>',"1 token listed.","all")
        self.assertEqual(self.store.events()[0]["kind"],"listing")

    def test_public_json_token_arrival_and_later_ca(self):
        self.detector.scan_json({"tokens":[{"id":"a","name":"Alpha","symbol":"A"}]},BASE+"/api/tokens")
        self.detector.scan_json({"tokens":[{"id":"a","name":"Alpha","symbol":"A","mint":EVM}]},BASE+"/api/tokens")
        self.assertEqual(sorted(e["kind"] for e in self.store.events()),["address","token"])

    def test_delivery_and_ack_persist(self):
        self.detector.deployment({"enabled":True})
        event=self.store.events()[0]
        self.store.ack([event["id"]],"sound")
        self.assertEqual(self.store.events(pending="sound"),[])
        self.assertIsNone(self.store.events()[0]["acknowledged_at"])
        self.store.ack([event["id"]])
        self.assertIsNotNone(self.store.events()[0]["acknowledged_at"])

    def test_exact_eight_beeps(self):
        calls,pauses=[],[]
        beep_sequence(lambda hz,ms:calls.append((hz,ms)),pauses.append)
        self.assertEqual(calls,[(888,888)]*8)
        self.assertEqual(pauses,[0.12]*7)

    def test_public_url_does_not_allow_private_or_foreign(self):
        for url in ("https://twice.fun.evil.example/api/tokens","http://twice.fun/","https://twice.fun/api/admin/pools","https://twice.fun/api/auth/session","https://u@twice.fun/"):
            self.assertFalse(public_url(url))
        self.assertTrue(public_url(BASE+"/api/deployment"))

    def test_respects_retry_after(self):
        self.assertEqual(retry_delay({"Retry-After":"120"},1),120)
        self.assertGreaterEqual(retry_delay({},4),16)

if __name__=="__main__":
    unittest.main()
