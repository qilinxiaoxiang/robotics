"""Summaries of results/<stage>.jsonl: per pose the worst case over its rows, and per row fall time, max tilt after 5 s,
end pitch and the pitch drift over the last 20 s (deg per 10 s; trace sampled every 5 s).

  python3 analyze.py combo [--group-by pose|label]"""
import collections, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))


def rows(stage):
    return [json.loads(l) for l in open(os.path.join(HERE, 'results', stage + '.jsonl'))]


def drift(r):
    tr = r.get('trace') or []
    if r['fell_at'] is not None or len(tr) < 5:
        return None
    return round((tr[-1][2] - tr[-5][2]) / ((tr[-1][0] - tr[-5][0]) / 10), 2)


def pose_key(label):
    return label.split(' a head')[0].split(' b head')[0]


if __name__ == '__main__':
    st = sys.argv[1]
    R = rows(st)
    g = collections.defaultdict(list)
    for r in R:
        g[pose_key(r['label'])].append(r)
    summ = []
    for k, rs in g.items():
        fell = [r['label'].split()[-1] + '@' + str(r['fell_at']) for r in rs if r['fell_at'] is not None]
        worst = max(r['max_tilt_after_5s'] for r in rs if r['fell_at'] is None) if any(r['fell_at'] is None for r in rs) else None
        ends = [(r['label'].split()[-1], r['end_pitch'], drift(r)) for r in rs]
        summ.append((len(fell), worst if worst is not None else 99, k, fell, ends))
    for n, w, k, fell, ends in sorted(summ):
        print(f'{k:24s} falls {fell} worst_tilt {w} | ' + ' '.join(f'{h}:{e:+.1f}({d})' for h, e, d in ends))
