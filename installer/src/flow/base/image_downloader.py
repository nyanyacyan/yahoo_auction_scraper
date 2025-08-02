# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$
# import
import logging

# このモジュール専用のロガーインスタンスを取得
# ※ 実際の出力先・出力レベルは、呼び出し元（上位）で設定されることを想定
logger = logging.getLogger(__name__)
# $$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$$

# **********************************************************************************
# class定義
class ImageDownloader:
    """
    Yahoo!オークション商品画像URLを
    GoogleスプレッドシートのIMAGE式（=IMAGE("url", 4, 80, 80)）
    に変換するだけの純粋な（副作用なし）ユーティリティクラス。

    ※ 画像のダウンロード・リサイズ・保存は一切しません。
    """

    # ------------------------------------------------------------------------------
    # 静的メソッド（インスタンス化不要で利用可能）
    @staticmethod
    def get_image_formula(image_url: str) -> str:
        """
        画像URLをスプレッドシート貼付用IMAGE式へ変換して返す

        Args:
            image_url (str): 商品画像のURL

        Returns:
            str: Google Sheets用のIMAGE式
            例 '=IMAGE("画像URL", 4, 80, 80)'

        Raises:
            ValueError: 不正なURL（空文字/None/strでない）なら例外
        """
        # URL未指定または型不一致時はエラーで即返す
        if not image_url or not isinstance(image_url, str):
            logger.error("画像URLが不正です: %r", image_url)
            raise ValueError("画像URLが不正です")
        
        # IMAGE関数フォーマットに変換
        formula = f'=IMAGE("{image_url}", 4, 80, 80)'
        
        # DEBUGログ（通常は出力されない・開発時のみ）
        logger.debug(f"IMAGE式生成: {formula}")
        return formula