"""Edge cases for q2_rules.baseline (inputs the running car could actually receive)."""
import math
from q2_rules import baseline
nan = float('nan')
T = [  # (name, args, expected decision)
 ("exactly 0.5 red + V2X red (>= threshold)",        (0.5, 0.0, 'red'),   'STOP'),
 ("just below 0.5 red + V2X red",                    (0.499, 0.0, 'red'), 'SLOW'),
 ("person exactly 0.9",                              (0.0, 0.9, 'green'), 'STOP'),
 ("person exactly 0.5",                              (0.0, 0.5, 'green'), 'SLOW'),
 ("both clean green",                                (0.01, 0.01, 'green'), 'GO'),
 ("camera red 0.99, V2X green (conflict)",           (0.99, 0.0, 'green'), 'SLOW'),
 ("V2X message missing (None), camera clean",        (0.01, 0.01, None),  'GO'),
 ("V2X message missing, camera red 0.99",            (0.99, 0.0, None),   'SLOW'),
 ("red_score NaN, V2X red",                          (nan, 0.0, 'red'),   'SLOW'),
 ("person_score NaN, otherwise clean",               (0.01, nan, 'green'), 'SLOW'),
 ("all evidence missing",                            (None, None, None),  'SLOW'),
 ("person_score NaN but red agreement",              (0.9, nan, 'red'),   'STOP'),
 ("score above 1 treated as invalid",                (1.2, 0.0, 'red'),   'SLOW'),
 ("negative score treated as invalid",               (-0.1, 0.0, 'green'), 'SLOW'),
 ("string score 'abc' treated as invalid",           ('abc', 0.0, 'green'), 'SLOW'),
 ("light string 'Red ' normalised",                  (0.9, 0.0, 'Red '),  'STOP'),
 ("unknown light 'yellow' = no message",             (0.01, 0.01, 'yellow'), 'GO'),
 ("person 0.95 beats green agreement",               (0.0, 0.95, 'green'), 'STOP'),
]
bad = 0
for name, a, exp in T:
    d, why = baseline(*a); ok = d == exp; bad += not ok
    print(f"{'PASS' if ok else 'FAIL'}  {name:46s} -> {d:4s} ({why})")
# statelessness: same input twice, order independent
assert baseline(0.9, 0.1, 'red') == baseline(0.9, 0.1, 'red')
print('\nfailures:', bad)
