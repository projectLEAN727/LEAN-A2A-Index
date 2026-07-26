import sys
import os
import unittest

# プロジェクトルートを追加
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from settlement import settlement_proxy

class TestProxyStrict(unittest.TestCase):
    def test_mock_mode_is_false(self):
        # 1. MOCK_MODE が確実に False であることの検証
        print(f"[*] Checking MOCK_MODE: {settlement_proxy.MOCK_MODE}")
        self.assertFalse(settlement_proxy.MOCK_MODE, "MOCK_MODE must be False in production.")

    def test_mock_tx_is_rejected(self):
        # 2. モックトランザクション (0x_mock_) がバイパスされずに弾かれることの検証
        print("[*] Testing mock transaction hash rejection...")
        # 0x_mock_ で始まるハッシュが False を返す（モックバイパスがパージされたことの証明）
        mock_tx_hash = "0x_mock_successful_payment_hash"
        result = settlement_proxy.verify_payment_transaction(mock_tx_hash, 1000, settlement_proxy.MASTER_WALLET)
        self.assertFalse(result, "Mock transaction hash must be rejected.")

    def test_invalid_tx_is_rejected(self):
        # 3. 存在しない不正なトランザクションが False を返すことの検証
        print("[*] Testing invalid transaction rejection...")
        invalid_tx_hash = "0x0000000000000000000000000000000000000000000000000000000000000000"
        result = settlement_proxy.verify_payment_transaction(invalid_tx_hash, 1000, settlement_proxy.MASTER_WALLET)
        self.assertFalse(result, "Invalid transaction must be rejected.")

if __name__ == "__main__":
    unittest.main()
