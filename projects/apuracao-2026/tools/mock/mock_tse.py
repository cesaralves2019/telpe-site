"""Mock of the TSE 2026 results tree, for testing the page without the real thing.
python mock_tse.py waiting|live|done  → writes mock/oficial/... then serve with serve.py"""
import json, os, random, sys

MODE = sys.argv[1] if len(sys.argv) > 1 else "live"
HG = sys.argv[2] if len(sys.argv) > 2 else "20:05:12"
FRAC = float(sys.argv[3]) if len(sys.argv) > 3 else None
SPLIT = float(sys.argv[4]) if len(sys.argv) > 4 else 0.506
ROOT = os.path.join(os.path.dirname(__file__), "mock", "oficial")
random.seed(7)
UFS = "ac al ap am ba ce df es go ma mt ms mg pa pb pr pe pi rj rn rs ro rr sc sp se to".split()
CANDS = [("13", "LULA", "LUIZ INÁCIO LULA DA SILVA", "PT", "280001607829"), ("22", "FLÁVIO BOLSONARO", "FLÁVIO NANTES BOLSONARO", "PL", "280001607830")]
CITIES_ZZ = [("30007", "DUBLIN"), ("30015", "LISBOA"), ("30023", "LONDRES"), ("30031", "TOQUIO"), ("30040", "NOVA IORQUE"), ("30058", "MIAMI"), ("30066", "PARIS"), ("30074", "BOSTON"), ("30082", "SYDNEY"), ("30090", "MADRI"), ("30104", "BERLIM"), ("30112", "PORTO")]
CITIES_PR = [("75353", "CURITIBA"), ("77771", "LONDRINA"), ("76910", "MARINGA")]
CITIES_SC = [("80284", "CAIBI"), ("81051", "FLORIANOPOLIS")]
GOV_UFS = ["sp", "rj", "rs", "pe", "pa"]


def pct(x): return f"{x:.2f}".replace(".", ",")


def unified(ele, abr, cargo, cands, total_sections, done_frac, split, elected_idx=None, nmn="Presidente"):
    done = int(total_sections * done_frac)
    voters = total_sections * 320
    est = done * 320
    turnout = int(est * 0.79)
    valid = int(turnout * 0.94)
    blank = int(turnout * 0.02)
    nul = turnout - valid - blank
    va = int(valid * split)
    rest = valid - va
    votes = [va] + ([rest] if len(cands) == 2 else [int(rest * 0.85), rest - int(rest * 0.85)] + [0] * (len(cands) - 3))
    out = {"ele": ele, "tpabr": "UF" if abr not in ("br",) else "BR", "cdabr": abr.upper(), "dg": "25/10/2026", "hg": HG if done else "", "dt": "25/10/2026" if done else "", "ht": "20:05:00" if done else "", "f": "o",
           "s": {"ts": str(total_sections), "st": str(done), "pst": pct(100 * done / total_sections if total_sections else 0)},
           "e": {"te": str(voters), "est": str(est), "c": str(turnout), "pc": pct(100 * turnout / est if est else 0), "a": str(est - turnout), "pa": pct(100 * (est - turnout) / est if est else 0)},
           "v": {"tv": str(turnout), "vv": str(valid), "pvv": "100,00", "pvvc": pct(100 * valid / turnout if turnout else 0), "vb": str(blank), "pvb": pct(100 * blank / turnout if turnout else 0), "vn": str(nul), "pvn": pct(100 * nul / turnout if turnout else 0), "tvn": str(nul), "ptvn": pct(100 * nul / turnout if turnout else 0)},
           "carg": [{"cd": str(cargo), "nmn": nmn, "nv": "1", "agr": []}]}
    for i, (n, nmu, nm, sg, sq) in enumerate(cands):
        out["carg"][0]["agr"].append({"seq": str(i + 1), "par": [{"sg": sg, "n": n, "cand": [{"seq": str(i + 1), "sqcand": sq, "n": n, "nm": nm, "nmu": nmu, "vap": str(votes[i]), "pvap": pct(100 * votes[i] / valid if valid else 0), "e": "s" if (elected_idx == i or (ele in ("6257", "6259") and i < 2)) else "n", "st": "Eleito" if elected_idx == i else ("2º turno" if ele in ("6257", "6259") and i < 2 else "")}]}]})
    return out


def write(path, obj):
    full = os.path.join(ROOT, path)
    os.makedirs(os.path.dirname(full), exist_ok=True)
    with open(full, "w", encoding="utf-8") as f:
        json.dump(obj, f, ensure_ascii=False)


frac = {"waiting": 0.0, "live": 0.83, "done": 1.0}[MODE] if FRAC is None else FRAC
elected = 0 if MODE == "done" else None
# config
write("comum/config/ele-c.json", {"dg": "25/10/2026", "hg": "08:00:00", "pl": [
    {"dt": "04/10/2026", "e": [{"cd": "6257", "cdt": "Eleição Geral Federal 2026", "t": "1", "abr": [{"cd": "BR", "cp": [{"cd": "1", "ds": "Presidente"}]}]}, {"cd": "6259", "t": "1", "abr": [{"cd": u.upper(), "cp": [{"cd": "3", "ds": "Governador"}, {"cd": "5", "ds": "Senador"}]} for u in UFS]}]},
    {"dt": "25/10/2026", "e": [{"cd": "6258", "cdt": "Eleição Geral Federal 2026 - 2º turno", "t": "2", "abr": [{"cd": "BR", "cp": [{"cd": "1", "ds": "Presidente"}]}]}, {"cd": "6260", "cdt": "Eleição Geral Estadual 2026 - 2º turno", "t": "2", "abr": [{"cd": u.upper(), "cp": [{"cd": "3", "ds": "Governador"}]} for u in GOV_UFS]}]}]})
# first round recap
write("ele2026/6257/dados/br/br-c0001-e006257-u.json", unified("6257", "br", 1, CANDS + [("12", "CIRO GOMES", "CIRO FERREIRA GOMES", "PDT", "280001607831")], 496512, 1.0, 0.49))
# first round per UF (prior for the projection): a UF-specific split, same seed each run
rs = random.Random(3)
for uf in UFS + ["zz"]:
    write(f"ele2026/6257/dados/{uf}/{uf}-c0001-e006257-u.json", unified("6257", uf, 1, CANDS + [("12", "CIRO GOMES", "CIRO FERREIRA GOMES", "PDT", "280001607831")], rs.randint(1500, 60000) if uf != "zz" else 1200, 1.0, rs.uniform(0.3, 0.7)))
# first round for the spotlight cities, the other PR/SC cities and the exterior cities; first round for governors (3 candidates)
for c, n in CITIES_PR:
    write(f"ele2026/6257/dados/pr/pr{c}-c0001-e006257-u.json", unified("6257", "pr", 1, CANDS + [("12", "CIRO GOMES", "CIRO FERREIRA GOMES", "PDT", "280001607831")], 3200 if n == "CURITIBA" else 900, 1.0, 0.44))
for c, n in CITIES_SC:
    write(f"ele2026/6257/dados/sc/sc{c}-c0001-e006257-u.json", unified("6257", "sc", 1, CANDS + [("12", "CIRO GOMES", "CIRO FERREIRA GOMES", "PDT", "280001607831")], 12 if n == "CAIBI" else 1400, 1.0, 0.39))
for c, n in CITIES_ZZ:
    write(f"ele2026/6257/dados/zz/zz{c}-c0001-e006257-u.json", unified("6257", "zz", 1, CANDS + [("12", "CIRO GOMES", "CIRO FERREIRA GOMES", "PDT", "280001607831")], rs.randint(3, 60), 1.0, rs.uniform(0.35, 0.7)))
# municipalities list
write("ele2026/6258/config/mun-e006258-cm.json", {"dg": "25/10/2026", "abr": [{"cd": "PR", "ds": "PARANÁ", "mu": [{"cd": c, "nm": n} for c, n in CITIES_PR]}, {"cd": "SP", "ds": "SÃO PAULO", "mu": [{"cd": "71072", "nm": "SÃO PAULO"}]}, {"cd": "SC", "ds": "SANTA CATARINA", "mu": [{"cd": c, "nm": n} for c, n in CITIES_SC]}, {"cd": "ZZ", "ds": "EXTERIOR", "mu": [{"cd": c, "nm": n} for c, n in CITIES_ZZ]}]})
# president: br, ufs, zz
write("ele2026/6258/dados/br/br-c0001-e006258-u.json", unified("6258", "br", 1, CANDS, 496512, frac, SPLIT, elected))
for uf in UFS + ["zz"]:
    write(f"ele2026/6258/dados/{uf}/{uf}-c0001-e006258-u.json", unified("6258", uf, 1, CANDS, random.randint(1500, 60000) if uf != "zz" else 1200, min(1.0, frac * random.uniform(0.85, 1.15)) if frac else 0, random.uniform(0.3, 0.72), elected))
for c, n in CITIES_PR:
    write(f"ele2026/6258/dados/pr/pr{c}-c0001-e006258-u.json", unified("6258", "pr", 1, CANDS, 3200 if n == "CURITIBA" else 900, min(1.0, frac * 1.05) if frac else 0, 0.41, elected))
for c, n in CITIES_SC:
    write(f"ele2026/6258/dados/sc/sc{c}-c0001-e006258-u.json", unified("6258", "sc", 1, CANDS, 12 if n == "CAIBI" else 1400, min(1.0, frac * 1.1) if frac else 0, 0.37, elected))
for c, n in CITIES_ZZ:
    write(f"ele2026/6258/dados/zz/zz{c}-c0001-e006258-u.json", unified("6258", "zz", 1, CANDS, random.randint(3, 60), (1.0 if random.random() < 0.8 else 0.5) if frac else 0, random.uniform(0.35, 0.7), elected))
# governors
GOVC = {"sp": [("45", "TARCISIO", "TARCÍSIO DE FREITAS", "REPUBLICANOS", "250001"), ("13", "HADDAD", "FERNANDO HADDAD", "PT", "250002")], "rj": [("22", "CASTRO", "CLÁUDIO CASTRO", "PL", "250003"), ("40", "FREIXO", "MARCELO FREIXO", "PSB", "250004")], "rs": [("55", "LEITE", "EDUARDO LEITE", "PSD", "250005"), ("13", "PONT", "RAUL PONT", "PT", "250006")], "pe": [("40", "JOÃO CAMPOS", "JOÃO CAMPOS", "PSB", "250007"), ("15", "RAQUEL", "RAQUEL LYRA", "MDB", "250008")], "pa": [("15", "HELDER", "HELDER BARBALHO", "MDB", "250009"), ("22", "ÉDER MAURO", "ÉDER MAURO", "PL", "250010")]}
for uf in GOV_UFS:
    write(f"ele2026/6259/dados/{uf}/{uf}-c0003-e006259-u.json", unified("6259", uf, 3, GOVC[uf] + [("30", "TERCEIRO", "CANDIDATO TERCEIRO", "NOVO", "250099")], 30000, 1.0, 0.47, None, nmn="Governador"))
    write(f"ele2026/6260/dados/{uf}/{uf}-c0003-e006260-u.json", unified("6260", uf, 3, GOVC[uf], 30000, frac, random.uniform(0.44, 0.6), elected, nmn="Governador"))
print("mock written:", MODE, ROOT)
