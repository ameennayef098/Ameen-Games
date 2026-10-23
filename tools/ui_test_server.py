# -*- coding: utf-8 -*-
"""خادم مؤقت لاختبار واجهة الاستيراد آليًا.

يشغّل نسخة من server.py على منفذ مختلف مع رمز مشرف معروف، حتى يستطيع
Playwright فتح لوحة الإدارة دون كلمة المرور الحقيقية. لا يلمس هذا الملف
أي شيء في المشروع ولا يبقى بعد الاختبار.
"""
import os
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

import server  # noqa: E402

TOKEN = 'uitest-token'
server.ADMIN_TOKENS.add(TOKEN)
print('uittest token:', TOKEN)
print('listening on http://127.0.0.1:5599')
server.app.run(host='127.0.0.1', port=5599, debug=False, use_reloader=False)
