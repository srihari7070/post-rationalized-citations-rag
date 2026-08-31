"""Measure a chapter against document/style/STYLE_PROFILE.md targets."""
import re, statistics, sys, pathlib
HEDGE = r"\b(may|might|appears?|suggests?|seems?|likely|unlikely|possibly|probably|roughly|approximately|arguably|apparently|tends? to|somewhat|largely|generally|potentially|plausibl\w+|not necessarily|to some extent|one reading|well)\b"
ENGAGE = r"\b(we|our|us|you|this thesis|this study|consider|note that|recall)\b"
NOMIN = r"\b\w{4,}(tion|ment|ness|ity|ance|ence)s?\b"
BANNED = ["delve","leverage","it is worth noting","furthermore","moreover","landscape",
          "realm","testament to","underscore","meticulous","crucial","foster","pivotal"]
def measure(text, label):
    body = re.sub(r"^\s*\|.*$", "", text, flags=re.M)
    body = re.sub(r"```.*?```", "", body, flags=re.S)
    body = re.sub(r"^#.*$", "", body, flags=re.M)
    sents = [s.strip() for s in re.split(r"(?<=[.!?])\s+", body) if len(s.split()) > 2]
    lens = [len(s.split()) for s in sents]; words = len(body.split()); k = words/1000
    nom = len(re.findall(NOMIN, body, re.I))/k
    hed = len(re.findall(HEDGE, body, re.I))/k
    eng = len(re.findall(ENGAGE, body, re.I))/k
    sd  = statistics.pstdev(lens)
    em  = body.count(chr(8212)); sc = body.count(';')
    ban = sum(len(re.findall(re.escape(b), body, re.I)) for b in BANNED)
    f = lambda v, lo, hi: "ok " if lo <= v <= hi else "OFF"
    print(f"{label:<20} {words:>6,}w  sd {sd:>5.1f} {f(sd,12.5,17)}  nom {nom:>5.1f} {f(nom,0,30)}"
          f"  hedge {hed:>5.1f} {f(hed,7.5,14)}  eng {eng:>5.1f} {f(eng,33,60)}"
          f"  em {em} sc {sc} ban {ban}")
if __name__ == "__main__":
    for a in sys.argv[1:]:
        measure(pathlib.Path(a).read_text(), pathlib.Path(a).stem)
