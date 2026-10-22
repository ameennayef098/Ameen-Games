#!/usr/bin/env python3
"""Assign a classification (تصنيف) to every category.

The category picker groups categories under coloured section headers the way a
catalogue does — science under «علوم», sport under «رياضة», and so on — instead
of one flat list of 59 entries.
"""
import json
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
CAT_FILE = os.path.join(BASE, 'data', 'categories', 'categories.json')

GROUPS = {
    'علوم': ['science', 'physics', 'chemistry', 'biology', 'space', 'space_missions',
             'human_body', 'solar_energy', 'weather_climate', 'seas_oceans', 'agriculture'],
    'رياضة': ['sports', 'basketball', 'football_arab', 'football_world', 'olympics'],
    'تقنية': ['tech', 'internet', 'smartphones', 'cybersecurity', 'ai_ml',
              'aviation', 'transport', 'energy'],
    'تاريخ وحضارات': ['history', 'history_figures', 'world_wars', 'kings_leaders',
                     'landmarks', 'pharaohs', 'islamic_history', 'tourism'],
    'جغرافيا ودول': ['geography', 'countries', 'kingdom', 'e6e3c106'],
    'دين وثقافة إسلامية': ['islamic', 'quran', 'prophets', 'seerah'],
    'فن وإعلام': ['movies', 'music', 'arts', 'novels', 'india_cinema', 'anime'],
    'لغة وأدب': ['literature', 'arabic'],
    'معلومات عامة': ['general', 'puzzles', 'math', 'economy', 'inventions',
                    'currencies', 'food', 'health', 'animals_wild'],
}

GROUP_META = {
    'علوم': {'icon': '🔬', 'color': '#3b82f6'},
    'رياضة': {'icon': '⚽', 'color': '#10b981'},
    'تقنية': {'icon': '💻', 'color': '#6366f1'},
    'تاريخ وحضارات': {'icon': '📜', 'color': '#f59e0b'},
    'جغرافيا ودول': {'icon': '🌍', 'color': '#8b5cf6'},
    'دين وثقافة إسلامية': {'icon': '🕌', 'color': '#22c55e'},
    'فن وإعلام': {'icon': '🎬', 'color': '#ef4444'},
    'لغة وأدب': {'icon': '📚', 'color': '#ec4899'},
    'معلومات عامة': {'icon': '💡', 'color': '#06b6d4'},
}


def main():
    cats = json.load(open(CAT_FILE, encoding='utf-8'))
    by_id = {c['id']: c for c in cats}
    unknown = []
    for group, ids in GROUPS.items():
        meta = GROUP_META[group]
        for cid in ids:
            c = by_id.get(cid)
            if not c:
                unknown.append(cid)
                continue
            c['group'] = group
            c['group_icon'] = meta['icon']
            c['group_color'] = meta['color']
    assigned = {c.get('group') for c in cats if c.get('group')}
    for c in cats:
        if not c.get('group'):
            c['group'] = 'عام'
            c.setdefault('group_icon', '🗂️')
            c.setdefault('group_color', '#71769a')
    with open(CAT_FILE, 'w', encoding='utf-8') as f:
        json.dump(cats, f, ensure_ascii=False, indent=2)
    print('categories:', len(cats))
    print('groups:', sorted(assigned))
    if unknown:
        print('MISSING ids:', unknown)
        return 1
    for g in sorted(assigned):
        n = len([c for c in cats if c.get('group') == g])
        print('  %-22s %d' % (g, n))
    return 0


if __name__ == '__main__':
    sys.exit(main())
