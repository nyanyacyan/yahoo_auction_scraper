import logging
import re

# 汎用タグ検出（<div ...> / \u003cdiv ...> / <!-- ... --> など幅広くヒット）
_TAG_ANY = re.compile(
    r"(?:<|\\u003c)\s*/?\s*[a-zA-Z!][^>]{0,5000}(?:>|\\u003e)",
    re.IGNORECASE | re.DOTALL,
)

# 明示的に重いブロック（script/style/iframe）を優先的に畳む
_BLOCKS = [
    (re.compile(r"<script[^>]*>.*?</script>", re.IGNORECASE | re.DOTALL), "script"),
    (re.compile(r"\\u003cscript[^>]*>.*?\\u003c/script\\u003e", re.IGNORECASE | re.DOTALL), "script"),
    (re.compile(r"<style[^>]*>.*?</style>", re.IGNORECASE | re.DOTALL), "style"),
    (re.compile(r"\\u003cstyle[^>]*>.*?\\u003c/style\\u003e", re.IGNORECASE | re.DOTALL), "style"),
    (re.compile(r"<iframe[^>]*>.*?</iframe>", re.IGNORECASE | re.DOTALL), "iframe"),
    (re.compile(r"\\u003ciframe[^>]*>.*?\\u003c/iframe\\u003e", re.IGNORECASE | re.DOTALL), "iframe"),
]

# JSっぽい断片だけが単独で来た場合の保険（YAHOO系など良く出るキーワード）
_JS_MARKERS = ("customLoggerCore", "YAHOO.JP", "function(", "var ", "localStorage", "jQuery")

class HtmlJsTrimmer:
    MAX_TOTAL = 3000
    KEEP_HEAD = 1000
    KEEP_TAIL = 300

    @classmethod
    def _squash_remote_data(cls, s: str) -> str:
        # Selenium Remote response: data=... をピンポイントで潰す
        if "Remote response:" in s and " data=" in s:
            st = s.find(" data=") + len(" data=")
            ed = s.find(" | headers=", st)
            if ed == -1:
                ed = len(s)
            return f"{s[:st]}<omitted {ed-st} chars>{s[ed:]}"
        return s

    @classmethod
    def _squash_blocks(cls, s: str) -> str:
        # script/style/iframe は丸ごと置換
        for rx, kind in _BLOCKS:
            while True:
                m = rx.search(s)
                if not m:
                    break
                s = f"{s[:m.start()]}<HTML/JS {kind} omitted {m.end()-m.start()} chars>{s[m.end():]}"
        return s

    @classmethod
    def _squash_tag_spam(cls, s: str) -> str:
        # タグが多数ある場合は、最初のタグから最後のタグまでを丸ごと潰す
        matches = list(_TAG_ANY.finditer(s))
        if not matches:
            # JSキーワードが多く、セミコロンだらけ等 → JS塊として潰す
            if sum(k in s for k in _JS_MARKERS) >= 2 and (s.count(";") > 5 or len(s) > 500):
                return "<HTML/JS omitted {0} chars>".format(len(s))
            return s
        start = matches[0].start()
        end = matches[-1].end()
        return f"{s[:start]}<HTML/JS omitted {end-start} chars>{s[end:]}"

    @classmethod
    def _hard_cut(cls, s: str) -> str:
        if len(s) <= cls.MAX_TOTAL:
            return s
        omit = len(s) - (cls.KEEP_HEAD + cls.KEEP_TAIL)
        return f"{s[:cls.KEEP_HEAD]} ... [TRIMMED {omit} chars] ... {s[-cls.KEEP_TAIL:]}"

    @classmethod
    def sanitize(cls, s: str) -> str:
        s = cls._squash_remote_data(s)
        s = cls._squash_blocks(s)
        s = cls._squash_tag_spam(s)
        s = cls._hard_cut(s)
        return s


def install_log_trimmer() -> None:
    """
    すべての logger/handler にまたがって強制トリムするため、
    LogRecordFactory を差し替える（これが最も確実）。
    """
    old_factory = logging.getLogRecordFactory()
    def factory(*args, **kwargs):
        record = old_factory(*args, **kwargs)
        try:
            # msg と args を解決した文字列を一度作る
            rendered = record.getMessage()
            rendered = HtmlJsTrimmer.sanitize(rendered)
            record.msg = rendered
            record.args = ()
            if record.exc_text:
                record.exc_text = HtmlJsTrimmer.sanitize(record.exc_text)
        except Exception:
            pass
        return record
    logging.setLogRecordFactory(factory)