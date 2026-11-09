// ═══ بنك أسئلة «لودو الأسئلة والكروت» — 80 سؤالًا (40 ثقافة عامة + 40 رياضيات) ═══
// يمكنك التعديل أو الإضافة بنفس البنية:
// id: معرف فريد | category: general أو math | difficulty: 1-3
// question: نص السؤال | options: 4 خيارات | answer: فهرس الخيار الصحيح (يبدأ من 0) قبل الخلط
const QUESTION_BANK = [
  {
    "id": "GK-01",
    "category": "general",
    "difficulty": 1,
    "question": "ما أطول نهر في قارة إفريقيا؟",
    "options": [
      "نهر النيل",
      "نهر الكونغو",
      "نهر النيجر",
      "نهر الزمبيزي"
    ],
    "answer": 0
  },
  {
    "id": "GK-02",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة المملكة العربية السعودية؟",
    "options": [
      "الرياض",
      "جدة",
      "مكة المكرمة",
      "الدمام"
    ],
    "answer": 0
  },
  {
    "id": "GK-03",
    "category": "general",
    "difficulty": 1,
    "question": "كم عدد أيام السنة الميلادية غير الكبيسة؟",
    "options": [
      "365 يومًا",
      "360 يومًا",
      "364 يومًا",
      "366 يومًا"
    ],
    "answer": 0
  },
  {
    "id": "GK-04",
    "category": "general",
    "difficulty": 2,
    "question": "ما أكبر كوكب في المجموعة الشمسية؟",
    "options": [
      "المشتري",
      "زحل",
      "الأرض",
      "نبتون"
    ],
    "answer": 0
  },
  {
    "id": "GK-05",
    "category": "general",
    "difficulty": 2,
    "question": "ما أقرب كوكب إلى الشمس؟",
    "options": [
      "عطارد",
      "الزهرة",
      "المريخ",
      "الأرض"
    ],
    "answer": 0
  },
  {
    "id": "GK-06",
    "category": "general",
    "difficulty": 1,
    "question": "كم عدد قارات العالم؟",
    "options": [
      "سبع قارات",
      "خمس قارات",
      "ست قارات",
      "ثماني قارات"
    ],
    "answer": 0
  },
  {
    "id": "GK-07",
    "category": "general",
    "difficulty": 1,
    "question": "ما العنصر الكيميائي الذي رمزه الكيميائي O؟",
    "options": [
      "الأكسجين",
      "الذهب",
      "الهيدروجين",
      "النيتروجين"
    ],
    "answer": 0
  },
  {
    "id": "GK-08",
    "category": "general",
    "difficulty": 1,
    "question": "ما الحيوان الملقب بسفينة الصحراء؟",
    "options": [
      "الجمل",
      "الحصان",
      "الغزال",
      "الحمار الوحشي"
    ],
    "answer": 0
  },
  {
    "id": "GK-09",
    "category": "general",
    "difficulty": 2,
    "question": "ما أكبر محيطات العالم؟",
    "options": [
      "المحيط الهادي",
      "المحيط الأطلسي",
      "المحيط الهندي",
      "المحيط المتجمد الشمالي"
    ],
    "answer": 0
  },
  {
    "id": "GK-10",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة جمهورية مصر العربية؟",
    "options": [
      "القاهرة",
      "الإسكندرية",
      "الجيزة",
      "الأقصر"
    ],
    "answer": 0
  },
  {
    "id": "GK-11",
    "category": "general",
    "difficulty": 3,
    "question": "من العالم المسلم الذي يُنسب إليه تأسيس علم الجبر؟",
    "options": [
      "محمد بن موسى الخوارزمي",
      "ابن سينا",
      "البيروني",
      "ابن الهيثم"
    ],
    "answer": 0
  },
  {
    "id": "GK-12",
    "category": "general",
    "difficulty": 1,
    "question": "ما أصغر وحدة بنائية في جسم الكائن الحي؟",
    "options": [
      "الخلية",
      "النسيج",
      "العضو",
      "الجهاز"
    ],
    "answer": 0
  },
  {
    "id": "GK-13",
    "category": "general",
    "difficulty": 2,
    "question": "كم عدد أسنان الإنسان البالغ الكاملة؟",
    "options": [
      "32 سنًا",
      "28 سنًا",
      "30 سنًا",
      "34 سنًا"
    ],
    "answer": 0
  },
  {
    "id": "GK-14",
    "category": "general",
    "difficulty": 2,
    "question": "ما الغاز الذي تمتصه النباتات في عملية البناء الضوئي؟",
    "options": [
      "ثاني أكسيد الكربون",
      "الأكسجين",
      "النيتروجين",
      "الهيدروجين"
    ],
    "answer": 0
  },
  {
    "id": "GK-15",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة المملكة الأردنية الهاشمية؟",
    "options": [
      "عمّان",
      "الزرقاء",
      "إربد",
      "العقبة"
    ],
    "answer": 0
  },
  {
    "id": "GK-16",
    "category": "general",
    "difficulty": 1,
    "question": "كم عدد لاعبي فريق كرة القدم داخل الملعب؟",
    "options": [
      "11 لاعبًا",
      "9 لاعبين",
      "10 لاعبين",
      "12 لاعبًا"
    ],
    "answer": 0
  },
  {
    "id": "GK-17",
    "category": "general",
    "difficulty": 2,
    "question": "ما أسرع حيوان بري في العالم؟",
    "options": [
      "الفهد (الشيتا)",
      "الأسد",
      "الحصان",
      "الغزال"
    ],
    "answer": 0
  },
  {
    "id": "GK-18",
    "category": "general",
    "difficulty": 2,
    "question": "ما أكبر حيوان ثديي في العالم؟",
    "options": [
      "الحوت الأزرق",
      "الفيل الأفريقي",
      "الزرافة",
      "الحوت القاتل"
    ],
    "answer": 0
  },
  {
    "id": "GK-19",
    "category": "general",
    "difficulty": 2,
    "question": "ماذا يقيس جهاز البارومتر؟",
    "options": [
      "الضغط الجوي",
      "درجة الحرارة",
      "سرعة الرياح",
      "الرطوبة"
    ],
    "answer": 0
  },
  {
    "id": "GK-20",
    "category": "general",
    "difficulty": 1,
    "question": "كم عدد حروف اللغة العربية؟",
    "options": [
      "28 حرفًا",
      "26 حرفًا",
      "29 حرفًا",
      "30 حرفًا"
    ],
    "answer": 0
  },
  {
    "id": "GK-21",
    "category": "general",
    "difficulty": 1,
    "question": "ما البحر الذي يفصل بين مصر وشبه الجزيرة العربية؟",
    "options": [
      "البحر الأحمر",
      "البحر المتوسط",
      "بحر العرب",
      "الخليج العربي"
    ],
    "answer": 0
  },
  {
    "id": "GK-22",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة دولة الإمارات العربية المتحدة؟",
    "options": [
      "أبوظبي",
      "دبي",
      "الشارقة",
      "العين"
    ],
    "answer": 0
  },
  {
    "id": "GK-23",
    "category": "general",
    "difficulty": 2,
    "question": "من العالم الذي طوّر المصباح الكهربائي التجاري الأشهر؟",
    "options": [
      "توماس إديسون",
      "إسحاق نيوتن",
      "غراهام بيل",
      "أليساندرو فولتا"
    ],
    "answer": 0
  },
  {
    "id": "GK-24",
    "category": "general",
    "difficulty": 2,
    "question": "ما أكبر صحراء حارة في العالم؟",
    "options": [
      "الصحراء الكبرى",
      "صحراء الربع الخالي",
      "صحراء غوبي",
      "صحراء كالاهاري"
    ],
    "answer": 0
  },
  {
    "id": "GK-25",
    "category": "general",
    "difficulty": 1,
    "question": "ما الكوكب الملقب بالكوكب الأحمر؟",
    "options": [
      "المريخ",
      "زحل",
      "الزهرة",
      "عطارد"
    ],
    "answer": 0
  },
  {
    "id": "GK-26",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة جمهورية العراق؟",
    "options": [
      "بغداد",
      "البصرة",
      "الموصل",
      "أربيل"
    ],
    "answer": 0
  },
  {
    "id": "GK-27",
    "category": "general",
    "difficulty": 1,
    "question": "ماذا يُسمى صغير الأسد؟",
    "options": [
      "الشبل",
      "الجرو",
      "المهر",
      "الخروف"
    ],
    "answer": 0
  },
  {
    "id": "GK-28",
    "category": "general",
    "difficulty": 2,
    "question": "ما المعدن الذي يكون سائلًا في درجة حرارة الغرفة؟",
    "options": [
      "الزئبق",
      "الحديد",
      "النحاس",
      "الألمنيوم"
    ],
    "answer": 0
  },
  {
    "id": "GK-29",
    "category": "general",
    "difficulty": 3,
    "question": "من مؤلف كتاب (الأيام) الشهير؟",
    "options": [
      "طه حسين",
      "نجيب محفوظ",
      "توفيق الحكيم",
      "عباس محمود العقاد"
    ],
    "answer": 0
  },
  {
    "id": "GK-30",
    "category": "general",
    "difficulty": 2,
    "question": "ما السورة التي تُلقّب بقلب القرآن الكريم؟",
    "options": [
      "سورة يس",
      "سورة الفاتحة",
      "سورة البقرة",
      "سورة الرحمن"
    ],
    "answer": 0
  },
  {
    "id": "GK-31",
    "category": "general",
    "difficulty": 2,
    "question": "ما اللغة الأكثر تحدثًا في العالم كلغة أم؟",
    "options": [
      "الصينية (الماندرين)",
      "الإنجليزية",
      "العربية",
      "الإسبانية"
    ],
    "answer": 0
  },
  {
    "id": "GK-32",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة دولة الكويت؟",
    "options": [
      "مدينة الكويت",
      "الجهراء",
      "الأحمدي",
      "حولي"
    ],
    "answer": 0
  },
  {
    "id": "GK-33",
    "category": "general",
    "difficulty": 2,
    "question": "كم عدد عظام جسم الإنسان البالغ؟",
    "options": [
      "206 عظمة",
      "180 عظمة",
      "300 عظمة",
      "250 عظمة"
    ],
    "answer": 0
  },
  {
    "id": "GK-34",
    "category": "general",
    "difficulty": 2,
    "question": "ما الدولة الأكثر تتويجًا بكأس العالم لكرة القدم؟",
    "options": [
      "البرازيل",
      "ألمانيا",
      "إيطاليا",
      "الأرجنتين"
    ],
    "answer": 0
  },
  {
    "id": "GK-35",
    "category": "general",
    "difficulty": 1,
    "question": "ما اسم العلم الذي يدرس النجوم والأجرام السماوية؟",
    "options": [
      "الفلك",
      "الجيولوجيا",
      "الأحياء",
      "الكيمياء"
    ],
    "answer": 0
  },
  {
    "id": "GK-36",
    "category": "general",
    "difficulty": 3,
    "question": "ماذا يعني الاختصار USB في الحاسوب؟",
    "options": [
      "ناقل تسلسلي عام",
      "شبكة لاسلكية",
      "ذاكرة مؤقتة",
      "وحدة معالجة رسومية"
    ],
    "answer": 0
  },
  {
    "id": "GK-37",
    "category": "general",
    "difficulty": 1,
    "question": "ما أعلى قمة جبلية في العالم؟",
    "options": [
      "قمة إيفرست",
      "جبل كليمنجارو",
      "قمة كِ2",
      "جبل طوبوق"
    ],
    "answer": 0
  },
  {
    "id": "GK-38",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة المملكة المغربية؟",
    "options": [
      "الرباط",
      "الدار البيضاء",
      "مراكش",
      "فاس"
    ],
    "answer": 0
  },
  {
    "id": "GK-39",
    "category": "general",
    "difficulty": 1,
    "question": "ما الغاز الذي نتنفسه ويحتاجه الإنسان للبقاء على قيد الحياة؟",
    "options": [
      "الأكسجين",
      "ثاني أكسيد الكربون",
      "النيتروجين",
      "الهيليوم"
    ],
    "answer": 0
  },
  {
    "id": "GK-40",
    "category": "general",
    "difficulty": 1,
    "question": "كم عدد شهور السنة الميلادية؟",
    "options": [
      "12 شهرًا",
      "10 أشهر",
      "11 شهرًا",
      "13 شهرًا"
    ],
    "answer": 0
  },
  {
    "id": "MT-01",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 7 × 8؟",
    "options": [
      "56",
      "48",
      "54",
      "63"
    ],
    "answer": 0
  },
  {
    "id": "MT-02",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 12 + 27؟",
    "options": [
      "39",
      "29",
      "49",
      "37"
    ],
    "answer": 0
  },
  {
    "id": "MT-03",
    "category": "math",
    "difficulty": 2,
    "question": "كم ناتج 45 − 18؟",
    "options": [
      "27",
      "37",
      "23",
      "33"
    ],
    "answer": 0
  },
  {
    "id": "MT-04",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 9 × 6؟",
    "options": [
      "54",
      "56",
      "45",
      "63"
    ],
    "answer": 0
  },
  {
    "id": "MT-05",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 81 ÷ 9؟",
    "options": [
      "9",
      "8",
      "7",
      "11"
    ],
    "answer": 0
  },
  {
    "id": "MT-06",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 15 + 38؟",
    "options": [
      "53",
      "43",
      "63",
      "51"
    ],
    "answer": 0
  },
  {
    "id": "MT-07",
    "category": "math",
    "difficulty": 2,
    "question": "كم ناتج 63 − 29؟",
    "options": [
      "34",
      "44",
      "24",
      "36"
    ],
    "answer": 0
  },
  {
    "id": "MT-08",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 6 × 7؟",
    "options": [
      "42",
      "36",
      "48",
      "40"
    ],
    "answer": 0
  },
  {
    "id": "MT-09",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 120 ÷ 4؟",
    "options": [
      "30",
      "40",
      "24",
      "34"
    ],
    "answer": 0
  },
  {
    "id": "MT-10",
    "category": "math",
    "difficulty": 2,
    "question": "كم يساوي 25% من العدد 200؟",
    "options": [
      "50",
      "25",
      "75",
      "40"
    ],
    "answer": 0
  },
  {
    "id": "MT-11",
    "category": "math",
    "difficulty": 1,
    "question": "كم يساوي نصف العدد 150؟",
    "options": [
      "75",
      "70",
      "80",
      "65"
    ],
    "answer": 0
  },
  {
    "id": "MT-12",
    "category": "math",
    "difficulty": 2,
    "question": "كم ناتج 11 × 11؟",
    "options": [
      "121",
      "111",
      "101",
      "131"
    ],
    "answer": 0
  },
  {
    "id": "MT-13",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 100 − 47؟",
    "options": [
      "53",
      "63",
      "43",
      "57"
    ],
    "answer": 0
  },
  {
    "id": "MT-14",
    "category": "math",
    "difficulty": 2,
    "question": "كم ناتج 8 × 12؟",
    "options": [
      "96",
      "86",
      "108",
      "88"
    ],
    "answer": 0
  },
  {
    "id": "MT-15",
    "category": "math",
    "difficulty": 2,
    "question": "كم ناتج 3 × 3 × 3؟",
    "options": [
      "27",
      "9",
      "18",
      "21"
    ],
    "answer": 0
  },
  {
    "id": "MT-16",
    "category": "math",
    "difficulty": 2,
    "question": "كم ناتج 144 ÷ 12؟",
    "options": [
      "12",
      "14",
      "10",
      "16"
    ],
    "answer": 0
  },
  {
    "id": "MT-17",
    "category": "math",
    "difficulty": 2,
    "question": "كم ناتج 5 × 5 + 5؟",
    "options": [
      "30",
      "25",
      "35",
      "55"
    ],
    "answer": 0
  },
  {
    "id": "MT-18",
    "category": "math",
    "difficulty": 3,
    "question": "كم ناتج 2 + 2 × 3؟",
    "options": [
      "8",
      "12",
      "10",
      "6"
    ],
    "answer": 0
  },
  {
    "id": "MT-19",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 36 + 48؟",
    "options": [
      "84",
      "74",
      "94",
      "78"
    ],
    "answer": 0
  },
  {
    "id": "MT-20",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 90 − 36؟",
    "options": [
      "54",
      "64",
      "44",
      "56"
    ],
    "answer": 0
  },
  {
    "id": "MT-21",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 7 × 9؟",
    "options": [
      "63",
      "56",
      "72",
      "65"
    ],
    "answer": 0
  },
  {
    "id": "MT-22",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 48 ÷ 6؟",
    "options": [
      "8",
      "7",
      "9",
      "6"
    ],
    "answer": 0
  },
  {
    "id": "MT-23",
    "category": "math",
    "difficulty": 3,
    "question": "كم يساوي 1/2 + 1/4؟",
    "options": [
      "3/4",
      "2/6",
      "1/6",
      "2/4"
    ],
    "answer": 0
  },
  {
    "id": "MT-24",
    "category": "math",
    "difficulty": 2,
    "question": "كم يساوي 10% من العدد 350؟",
    "options": [
      "35",
      "30",
      "40",
      "3.5"
    ],
    "answer": 0
  },
  {
    "id": "MT-25",
    "category": "math",
    "difficulty": 2,
    "question": "كم ناتج 13 × 5؟",
    "options": [
      "65",
      "55",
      "75",
      "58"
    ],
    "answer": 0
  },
  {
    "id": "MT-26",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 72 ÷ 8؟",
    "options": [
      "9",
      "8",
      "7",
      "12"
    ],
    "answer": 0
  },
  {
    "id": "MT-27",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 60 − 23؟",
    "options": [
      "37",
      "47",
      "27",
      "43"
    ],
    "answer": 0
  },
  {
    "id": "MT-28",
    "category": "math",
    "difficulty": 2,
    "question": "كم ناتج 4 × 4 × 4؟",
    "options": [
      "64",
      "16",
      "48",
      "44"
    ],
    "answer": 0
  },
  {
    "id": "MT-29",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 18 + 76؟",
    "options": [
      "94",
      "84",
      "104",
      "88"
    ],
    "answer": 0
  },
  {
    "id": "MT-30",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 200 − 125؟",
    "options": [
      "75",
      "85",
      "65",
      "95"
    ],
    "answer": 0
  },
  {
    "id": "MT-31",
    "category": "math",
    "difficulty": 2,
    "question": "كم ناتج 12 × 12؟",
    "options": [
      "144",
      "124",
      "132",
      "164"
    ],
    "answer": 0
  },
  {
    "id": "MT-32",
    "category": "math",
    "difficulty": 2,
    "question": "كم ناتج 99 ÷ 11؟",
    "options": [
      "9",
      "8",
      "11",
      "7"
    ],
    "answer": 0
  },
  {
    "id": "MT-33",
    "category": "math",
    "difficulty": 2,
    "question": "كم ناتج 6 × 8 + 4؟",
    "options": [
      "52",
      "56",
      "48",
      "60"
    ],
    "answer": 0
  },
  {
    "id": "MT-34",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 25 × 4؟",
    "options": [
      "100",
      "80",
      "125",
      "90"
    ],
    "answer": 0
  },
  {
    "id": "MT-35",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 150 ÷ 5؟",
    "options": [
      "30",
      "25",
      "35",
      "20"
    ],
    "answer": 0
  },
  {
    "id": "MT-36",
    "category": "math",
    "difficulty": 1,
    "question": "كم يساوي 50% من العدد 90؟",
    "options": [
      "45",
      "40",
      "50",
      "30"
    ],
    "answer": 0
  },
  {
    "id": "MT-37",
    "category": "math",
    "difficulty": 3,
    "question": "كم ناتج 9 + 9 × 9؟",
    "options": [
      "90",
      "162",
      "81",
      "99"
    ],
    "answer": 0
  },
  {
    "id": "MT-38",
    "category": "math",
    "difficulty": 2,
    "question": "كم ناتج 84 ÷ 7؟",
    "options": [
      "12",
      "11",
      "13",
      "14"
    ],
    "answer": 0
  },
  {
    "id": "MT-39",
    "category": "math",
    "difficulty": 3,
    "question": "كم يساوي 3/4 من العدد 100؟",
    "options": [
      "75",
      "70",
      "80",
      "34"
    ],
    "answer": 0
  },
  {
    "id": "MT-40",
    "category": "math",
    "difficulty": 1,
    "question": "كم ناتج 20 + 30 − 15؟",
    "options": [
      "35",
      "45",
      "25",
      "65"
    ],
    "answer": 0
  }
];
