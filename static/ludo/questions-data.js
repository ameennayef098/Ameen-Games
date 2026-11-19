// ═══ بنك أسئلة «لودو الأسئلة والكروت» — 240 سؤالًا عبر 6 تصنيفات ═══
// التصنيفات: general ثقافة عامة | math رياضيات | science علوم وطبيعة
//            sports رياضة | tech تقنية وذكاء اصطناعي | islamic إسلاميات
// البنية: id معرف فريد | category التصنيف | difficulty الصعوبة 1-3
// question نص السؤال | options 4 خيارات | answer فهرس الصحيح (0-3) قبل الخلط
// الإجابة الصحيحة موزعة على الفهارس الأربعة، وتُخلط الخيارات عند العرض.
const QUESTION_BANK = [
  {
    "id": "GK-01",
    "category": "general",
    "difficulty": 1,
    "question": "ما أطول نهر في العالم؟",
    "options": [
      "نهر المسيسيبي",
      "نهر اليانغتسي",
      "نهر الأمازون",
      "نهر النيل"
    ],
    "answer": 3
  },
  {
    "id": "GK-02",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة المملكة العربية السعودية؟",
    "options": [
      "الدمام",
      "جدة",
      "مكة المكرمة",
      "الرياض"
    ],
    "answer": 3
  },
  {
    "id": "GK-03",
    "category": "general",
    "difficulty": 1,
    "question": "كم عدد أيام السنة الميلادية غير الكبيسة؟",
    "options": [
      "365 يومًا",
      "366 يومًا",
      "364 يومًا",
      "360 يومًا"
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
    "difficulty": 1,
    "question": "ما أقرب كوكب إلى الشمس؟",
    "options": [
      "الأرض",
      "المريخ",
      "عطارد",
      "الزهرة"
    ],
    "answer": 2
  },
  {
    "id": "GK-06",
    "category": "general",
    "difficulty": 1,
    "question": "كم عدد قارات العالم؟",
    "options": [
      "ست قارات",
      "سبع قارات",
      "ثماني قارات",
      "خمس قارات"
    ],
    "answer": 1
  },
  {
    "id": "GK-07",
    "category": "general",
    "difficulty": 1,
    "question": "ما العنصر الكيميائي الذي رمزه O؟",
    "options": [
      "النيتروجين",
      "الأكسجين",
      "الذهب",
      "الهيدروجين"
    ],
    "answer": 1
  },
  {
    "id": "GK-08",
    "category": "general",
    "difficulty": 1,
    "question": "ما الحيوان الملقب بسفينة الصحراء؟",
    "options": [
      "الجمل",
      "الحمار الوحشي",
      "الغزال",
      "الحصان"
    ],
    "answer": 0
  },
  {
    "id": "GK-09",
    "category": "general",
    "difficulty": 2,
    "question": "ما أكبر محيطات العالم؟",
    "options": [
      "المحيط المتجمد الشمالي",
      "المحيط الهادي",
      "المحيط الهندي",
      "المحيط الأطلسي"
    ],
    "answer": 1
  },
  {
    "id": "GK-10",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة جمهورية مصر العربية؟",
    "options": [
      "القاهرة",
      "الجيزة",
      "الإسكندرية",
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
      "ابن سينا",
      "ابن الهيثم",
      "محمد بن موسى الخوارزمي",
      "البيروني"
    ],
    "answer": 2
  },
  {
    "id": "GK-12",
    "category": "general",
    "difficulty": 1,
    "question": "ما أصغر وحدة بنائية في جسم الكائن الحي؟",
    "options": [
      "النسيج",
      "العضو",
      "الخلية",
      "الجهاز"
    ],
    "answer": 2
  },
  {
    "id": "GK-13",
    "category": "general",
    "difficulty": 2,
    "question": "كم عدد أسنان الإنسان البالغ الكاملة؟",
    "options": [
      "30 سنًا",
      "34 سنًا",
      "28 سنًا",
      "32 سنًا"
    ],
    "answer": 3
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
      "العقبة",
      "إربد",
      "الزرقاء"
    ],
    "answer": 0
  },
  {
    "id": "GK-16",
    "category": "general",
    "difficulty": 1,
    "question": "كم عدد لاعبي فريق كرة القدم داخل الملعب؟",
    "options": [
      "10 لاعبين",
      "9 لاعبين",
      "12 لاعبًا",
      "11 لاعبًا"
    ],
    "answer": 3
  },
  {
    "id": "GK-17",
    "category": "general",
    "difficulty": 2,
    "question": "ما أسرع حيوان بري في العالم؟",
    "options": [
      "الغزال",
      "الأسد",
      "النمر",
      "الفهد (الشيتا)"
    ],
    "answer": 3
  },
  {
    "id": "GK-18",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة اليابان؟",
    "options": [
      "طوكيو",
      "هيروشيما",
      "أوساكا",
      "كيوتو"
    ],
    "answer": 0
  },
  {
    "id": "GK-19",
    "category": "general",
    "difficulty": 1,
    "question": "كم عدد ألوان قوس قزح؟",
    "options": [
      "ستة ألوان",
      "سبعة ألوان",
      "خمسة ألوان",
      "ثمانية ألوان"
    ],
    "answer": 1
  },
  {
    "id": "GK-20",
    "category": "general",
    "difficulty": 2,
    "question": "ما أكبر دولة في العالم من حيث المساحة؟",
    "options": [
      "روسيا",
      "الصين",
      "كندا",
      "الولايات المتحدة"
    ],
    "answer": 0
  },
  {
    "id": "GK-21",
    "category": "general",
    "difficulty": 2,
    "question": "ما اللغة الرسمية في البرازيل؟",
    "options": [
      "الفرنسية",
      "الإسبانية",
      "الإنجليزية",
      "البرتغالية"
    ],
    "answer": 3
  },
  {
    "id": "GK-22",
    "category": "general",
    "difficulty": 1,
    "question": "ما الحيوان الملقب بملك الغابة؟",
    "options": [
      "النمر",
      "الذئب",
      "الدب",
      "الأسد"
    ],
    "answer": 3
  },
  {
    "id": "GK-23",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة فرنسا؟",
    "options": [
      "ليون",
      "مرسيليا",
      "باريس",
      "نيس"
    ],
    "answer": 2
  },
  {
    "id": "GK-24",
    "category": "general",
    "difficulty": 3,
    "question": "ما أطول سلسلة جبال في العالم؟",
    "options": [
      "جبال الهيمالايا",
      "جبال الأنديز",
      "جبال الألب",
      "جبال روكي"
    ],
    "answer": 1
  },
  {
    "id": "GK-25",
    "category": "general",
    "difficulty": 2,
    "question": "ما أكبر عضو في جسم الإنسان؟",
    "options": [
      "الجلد",
      "القلب",
      "الرئتان",
      "الكبد"
    ],
    "answer": 0
  },
  {
    "id": "GK-26",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة الإمارات العربية المتحدة؟",
    "options": [
      "دبي",
      "عجمان",
      "أبوظبي",
      "الشارقة"
    ],
    "answer": 2
  },
  {
    "id": "GK-27",
    "category": "general",
    "difficulty": 1,
    "question": "ما البحر الذي يفصل بين السعودية ومصر؟",
    "options": [
      "البحر الأحمر",
      "الخليج العربي",
      "بحر العرب",
      "البحر المتوسط"
    ],
    "answer": 0
  },
  {
    "id": "GK-28",
    "category": "general",
    "difficulty": 1,
    "question": "كم عدد حروف اللغة العربية؟",
    "options": [
      "29 حرفًا",
      "28 حرفًا",
      "30 حرفًا",
      "26 حرفًا"
    ],
    "answer": 1
  },
  {
    "id": "GK-29",
    "category": "general",
    "difficulty": 1,
    "question": "ما الحيوان الذي يغيّر لونه ليتموّه؟",
    "options": [
      "السلحفاة",
      "الحرباء",
      "الأفعى",
      "الضفدع"
    ],
    "answer": 1
  },
  {
    "id": "GK-30",
    "category": "general",
    "difficulty": 2,
    "question": "ما عاصمة المملكة المغربية؟",
    "options": [
      "الرباط",
      "فاس",
      "مراكش",
      "الدار البيضاء"
    ],
    "answer": 0
  },
  {
    "id": "GK-31",
    "category": "general",
    "difficulty": 2,
    "question": "ما أكبر صحراء حارة في العالم؟",
    "options": [
      "صحراء كالاهاري",
      "صحراء غوبي",
      "صحراء أتاكاما",
      "الصحراء الكبرى"
    ],
    "answer": 3
  },
  {
    "id": "GK-32",
    "category": "general",
    "difficulty": 2,
    "question": "كم عدد حروف اللغة الإنجليزية؟",
    "options": [
      "28 حرفًا",
      "26 حرفًا",
      "24 حرفًا",
      "30 حرفًا"
    ],
    "answer": 1
  },
  {
    "id": "GK-33",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة تركيا؟",
    "options": [
      "أنقرة",
      "إزمير",
      "بورصة",
      "إسطنبول"
    ],
    "answer": 0
  },
  {
    "id": "GK-34",
    "category": "general",
    "difficulty": 3,
    "question": "ما أصغر دولة في العالم من حيث المساحة؟",
    "options": [
      "الفاتيكان",
      "سان مارينو",
      "مالطا",
      "موناكو"
    ],
    "answer": 0
  },
  {
    "id": "GK-35",
    "category": "general",
    "difficulty": 3,
    "question": "كم عدد قلوب الأخطبوط؟",
    "options": [
      "قلب واحد",
      "قلبان",
      "أربعة قلوب",
      "ثلاثة قلوب"
    ],
    "answer": 3
  },
  {
    "id": "GK-36",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة العراق؟",
    "options": [
      "بغداد",
      "البصرة",
      "الموصل",
      "أربيل"
    ],
    "answer": 0
  },
  {
    "id": "GK-37",
    "category": "general",
    "difficulty": 2,
    "question": "ما أثقل حيوان بري في العالم؟",
    "options": [
      "الفيل الأفريقي",
      "فرس النهر",
      "وحيد القرن",
      "الزرافة"
    ],
    "answer": 0
  },
  {
    "id": "GK-38",
    "category": "general",
    "difficulty": 2,
    "question": "ما عملة اليابان؟",
    "options": [
      "الين",
      "اليوان",
      "الوون",
      "الدولار"
    ],
    "answer": 0
  },
  {
    "id": "GK-39",
    "category": "general",
    "difficulty": 1,
    "question": "ما عاصمة الكويت؟",
    "options": [
      "مدينة الكويت",
      "الجهراء",
      "الأحمدي",
      "حولي"
    ],
    "answer": 0
  },
  {
    "id": "GK-40",
    "category": "general",
    "difficulty": 1,
    "question": "ما الطائر الذي لا يطير ويعيش في القطب الجنوبي؟",
    "options": [
      "البجع",
      "النعامة",
      "البطريق",
      "الطاووس"
    ],
    "answer": 2
  },
  {
    "id": "MA-01",
    "category": "math",
    "difficulty": 1,
    "question": "ما ناتج 7 × 8؟",
    "options": [
      "48",
      "54",
      "56",
      "64"
    ],
    "answer": 2
  },
  {
    "id": "MA-02",
    "category": "math",
    "difficulty": 1,
    "question": "ما ناتج 144 ÷ 12؟",
    "options": [
      "11",
      "12",
      "16",
      "14"
    ],
    "answer": 1
  },
  {
    "id": "MA-03",
    "category": "math",
    "difficulty": 1,
    "question": "ما مساحة مربع طول ضلعه 5 سم؟",
    "options": [
      "10 سم²",
      "30 سم²",
      "20 سم²",
      "25 سم²"
    ],
    "answer": 3
  },
  {
    "id": "MA-04",
    "category": "math",
    "difficulty": 2,
    "question": "ما محيط مستطيل طوله 6 سم وعرضه 4 سم؟",
    "options": [
      "12 سم",
      "20 سم",
      "24 سم",
      "10 سم"
    ],
    "answer": 1
  },
  {
    "id": "MA-05",
    "category": "math",
    "difficulty": 2,
    "question": "كم يساوي 15% من 200؟",
    "options": [
      "25",
      "30",
      "35",
      "15"
    ],
    "answer": 1
  },
  {
    "id": "MA-06",
    "category": "math",
    "difficulty": 2,
    "question": "ما الجذر التربيعي للعدد 81؟",
    "options": [
      "7",
      "11",
      "8",
      "9"
    ],
    "answer": 3
  },
  {
    "id": "MA-07",
    "category": "math",
    "difficulty": 3,
    "question": "ما ناتج 2 أُس 5؟",
    "options": [
      "25",
      "64",
      "16",
      "32"
    ],
    "answer": 3
  },
  {
    "id": "MA-08",
    "category": "math",
    "difficulty": 1,
    "question": "ما مجموع زوايا المثلث الداخلية؟",
    "options": [
      "360 درجة",
      "90 درجة",
      "270 درجة",
      "180 درجة"
    ],
    "answer": 3
  },
  {
    "id": "MA-09",
    "category": "math",
    "difficulty": 1,
    "question": "ما ناتج 3/4 + 1/4؟",
    "options": [
      "2/4",
      "4/8",
      "3/8",
      "1"
    ],
    "answer": 3
  },
  {
    "id": "MA-10",
    "category": "math",
    "difficulty": 3,
    "question": "ما ناتج 0.5 × 0.2؟",
    "options": [
      "0.7",
      "0.1",
      "0.01",
      "1"
    ],
    "answer": 1
  },
  {
    "id": "MA-11",
    "category": "math",
    "difficulty": 1,
    "question": "كم عدد أضلاع الشكل السداسي؟",
    "options": [
      "8 أضلاع",
      "5 أضلاع",
      "6 أضلاع",
      "7 أضلاع"
    ],
    "answer": 2
  },
  {
    "id": "MA-12",
    "category": "math",
    "difficulty": 3,
    "question": "ما ناتج 9² − 4²؟",
    "options": [
      "25",
      "55",
      "77",
      "65"
    ],
    "answer": 3
  },
  {
    "id": "MA-13",
    "category": "math",
    "difficulty": 1,
    "question": "إذا كان س + 7 = 15، فما قيمة س؟",
    "options": [
      "8",
      "7",
      "22",
      "9"
    ],
    "answer": 0
  },
  {
    "id": "MA-14",
    "category": "math",
    "difficulty": 1,
    "question": "كم يساوي 25% من 80؟",
    "options": [
      "16",
      "20",
      "25",
      "40"
    ],
    "answer": 1
  },
  {
    "id": "MA-15",
    "category": "math",
    "difficulty": 3,
    "question": "ما محيط دائرة نصف قطرها 7 سم؟ (ط = 22/7)",
    "options": [
      "38 سم",
      "22 سم",
      "154 سم",
      "44 سم"
    ],
    "answer": 3
  },
  {
    "id": "MA-16",
    "category": "math",
    "difficulty": 1,
    "question": "ما ناتج 1000 − 387؟",
    "options": [
      "623",
      "613",
      "617",
      "713"
    ],
    "answer": 1
  },
  {
    "id": "MA-17",
    "category": "math",
    "difficulty": 3,
    "question": "ما ناتج مضروب العدد 6 (6!)؟",
    "options": [
      "5040",
      "120",
      "360",
      "720"
    ],
    "answer": 3
  },
  {
    "id": "MA-18",
    "category": "math",
    "difficulty": 2,
    "question": "ما مجموع زوايا الشكل الرباعي الداخلية؟",
    "options": [
      "180 درجة",
      "270 درجة",
      "360 درجة",
      "540 درجة"
    ],
    "answer": 2
  },
  {
    "id": "MA-19",
    "category": "math",
    "difficulty": 2,
    "question": "ما ناتج 3 أُس 4؟",
    "options": [
      "12",
      "64",
      "81",
      "27"
    ],
    "answer": 2
  },
  {
    "id": "MA-20",
    "category": "math",
    "difficulty": 1,
    "question": "ما نصف العدد 250؟",
    "options": [
      "100",
      "175",
      "125",
      "150"
    ],
    "answer": 2
  },
  {
    "id": "MA-21",
    "category": "math",
    "difficulty": 1,
    "question": "ما ناتج 12 × 12؟",
    "options": [
      "156",
      "144",
      "132",
      "124"
    ],
    "answer": 1
  },
  {
    "id": "MA-22",
    "category": "math",
    "difficulty": 2,
    "question": "أي من هذه الأعداد عدد أولي؟",
    "options": [
      "15",
      "17",
      "9",
      "21"
    ],
    "answer": 1
  },
  {
    "id": "MA-23",
    "category": "math",
    "difficulty": 2,
    "question": "ما مساحة مثلث قاعدته 10 سم وارتفاعه 6 سم؟",
    "options": [
      "30 سم²",
      "45 سم²",
      "60 سم²",
      "16 سم²"
    ],
    "answer": 0
  },
  {
    "id": "MA-24",
    "category": "math",
    "difficulty": 3,
    "question": "ما ناتج 45 ÷ 0.5؟",
    "options": [
      "9",
      "22.5",
      "90",
      "45.5"
    ],
    "answer": 2
  },
  {
    "id": "MA-25",
    "category": "math",
    "difficulty": 1,
    "question": "ما القيمة التقريبية للثابت ط (باي)؟",
    "options": [
      "2.14",
      "3.41",
      "3.14",
      "4.13"
    ],
    "answer": 2
  },
  {
    "id": "MA-26",
    "category": "math",
    "difficulty": 2,
    "question": "ما مجموع الأعداد من 1 إلى 10؟",
    "options": [
      "50",
      "55",
      "45",
      "60"
    ],
    "answer": 1
  },
  {
    "id": "MA-27",
    "category": "math",
    "difficulty": 1,
    "question": "إذا كان 3س = 27، فما قيمة س؟",
    "options": [
      "7",
      "8",
      "12",
      "9"
    ],
    "answer": 3
  },
  {
    "id": "MA-28",
    "category": "math",
    "difficulty": 2,
    "question": "ما حجم مكعب طول ضلعه 3 سم؟",
    "options": [
      "81 سم³",
      "18 سم³",
      "27 سم³",
      "9 سم³"
    ],
    "answer": 2
  },
  {
    "id": "MA-29",
    "category": "math",
    "difficulty": 2,
    "question": "الكسر 2/5 يساوي كم بالمئة؟",
    "options": [
      "50%",
      "40%",
      "60%",
      "25%"
    ],
    "answer": 1
  },
  {
    "id": "MA-30",
    "category": "math",
    "difficulty": 3,
    "question": "ما العدد التالي في المتتالية: 2، 6، 18، 54، ...؟",
    "options": [
      "180",
      "216",
      "108",
      "162"
    ],
    "answer": 3
  },
  {
    "id": "MA-31",
    "category": "math",
    "difficulty": 1,
    "question": "كم يساوي 10% من 350؟",
    "options": [
      "45",
      "30",
      "35",
      "40"
    ],
    "answer": 2
  },
  {
    "id": "MA-32",
    "category": "math",
    "difficulty": 3,
    "question": "ما مساحة دائرة نصف قطرها 3 سم تقريبًا؟ (ط ≈ 3.14)",
    "options": [
      "31.4 سم²",
      "18.84 سم²",
      "28.26 سم²",
      "9.42 سم²"
    ],
    "answer": 2
  },
  {
    "id": "MA-33",
    "category": "math",
    "difficulty": 1,
    "question": "ما ناتج 7 × 0 × 9؟",
    "options": [
      "7",
      "0",
      "9",
      "63"
    ],
    "answer": 1
  },
  {
    "id": "MA-34",
    "category": "math",
    "difficulty": 1,
    "question": "كم دقيقة في 3 ساعات؟",
    "options": [
      "150 دقيقة",
      "200 دقيقة",
      "120 دقيقة",
      "180 دقيقة"
    ],
    "answer": 3
  },
  {
    "id": "MA-35",
    "category": "math",
    "difficulty": 1,
    "question": "ما الجذر التربيعي للعدد 144؟",
    "options": [
      "11",
      "12",
      "16",
      "14"
    ],
    "answer": 1
  },
  {
    "id": "MA-36",
    "category": "math",
    "difficulty": 2,
    "question": "ما ناتج 8 × 7 − 6؟",
    "options": [
      "44",
      "62",
      "50",
      "56"
    ],
    "answer": 2
  },
  {
    "id": "MA-37",
    "category": "math",
    "difficulty": 2,
    "question": "إذا كان محيط مربع 36 سم، فما طول ضلعه؟",
    "options": [
      "6 سم",
      "9 سم",
      "12 سم",
      "8 سم"
    ],
    "answer": 1
  },
  {
    "id": "MA-38",
    "category": "math",
    "difficulty": 3,
    "question": "ما ناتج 2 أُس 10؟",
    "options": [
      "1024",
      "2048",
      "512",
      "256"
    ],
    "answer": 0
  },
  {
    "id": "MA-39",
    "category": "math",
    "difficulty": 3,
    "question": "ما مجموع أول خمسة أعداد فردية موجبة؟",
    "options": [
      "25",
      "30",
      "15",
      "20"
    ],
    "answer": 0
  },
  {
    "id": "MA-40",
    "category": "math",
    "difficulty": 2,
    "question": "ما ناتج 100 ÷ 4 ÷ 5؟",
    "options": [
      "25",
      "20",
      "5",
      "10"
    ],
    "answer": 2
  },
  {
    "id": "SC-01",
    "category": "science",
    "difficulty": 1,
    "question": "ما الغاز الذي يحتاجه الإنسان للتنفس؟",
    "options": [
      "الهيدروجين",
      "ثاني أكسيد الكربون",
      "النيتروجين",
      "الأكسجين"
    ],
    "answer": 3
  },
  {
    "id": "SC-02",
    "category": "science",
    "difficulty": 1,
    "question": "ما مركز المجموعة الشمسية؟",
    "options": [
      "الأرض",
      "القمر",
      "الشمس",
      "المشتري"
    ],
    "answer": 2
  },
  {
    "id": "SC-03",
    "category": "science",
    "difficulty": 2,
    "question": "كم عدد كواكب المجموعة الشمسية؟",
    "options": [
      "10 كواكب",
      "7 كواكب",
      "8 كواكب",
      "9 كواكب"
    ],
    "answer": 2
  },
  {
    "id": "SC-04",
    "category": "science",
    "difficulty": 1,
    "question": "ما الكوكب الملقب بالكوكب الأحمر؟",
    "options": [
      "المريخ",
      "الزهرة",
      "زحل",
      "عطارد"
    ],
    "answer": 0
  },
  {
    "id": "SC-05",
    "category": "science",
    "difficulty": 3,
    "question": "ما أقسى مادة طبيعية معروفة؟",
    "options": [
      "الجرافيت",
      "الماس",
      "الكوارتز",
      "الحديد"
    ],
    "answer": 1
  },
  {
    "id": "SC-06",
    "category": "science",
    "difficulty": 2,
    "question": "ما الرمز الكيميائي للذهب؟",
    "options": [
      "Go",
      "Gd",
      "Ag",
      "Au"
    ],
    "answer": 3
  },
  {
    "id": "SC-07",
    "category": "science",
    "difficulty": 2,
    "question": "ما الرمز الكيميائي للحديد؟",
    "options": [
      "Ir",
      "Fd",
      "In",
      "Fe"
    ],
    "answer": 3
  },
  {
    "id": "SC-08",
    "category": "science",
    "difficulty": 3,
    "question": "ما سرعة الضوء التقريبية في الفراغ؟",
    "options": [
      "150 ألف كم/ث",
      "3 ملايين كم/ث",
      "3 آلاف كم/ث",
      "300 ألف كم/ث"
    ],
    "answer": 3
  },
  {
    "id": "SC-09",
    "category": "science",
    "difficulty": 1,
    "question": "ما العضو الذي يضخ الدم في جسم الإنسان؟",
    "options": [
      "الكلى",
      "القلب",
      "الرئتان",
      "الكبد"
    ],
    "answer": 1
  },
  {
    "id": "SC-10",
    "category": "science",
    "difficulty": 3,
    "question": "كم عدد الكروموسومات في الخلية البشرية العادية؟",
    "options": [
      "46 كروموسومًا",
      "48 كروموسومًا",
      "44 كروموسومًا",
      "23 كروموسومًا"
    ],
    "answer": 0
  },
  {
    "id": "SC-11",
    "category": "science",
    "difficulty": 2,
    "question": "ما الغاز الأكثر وفرة في الغلاف الجوي للأرض؟",
    "options": [
      "الأرجون",
      "ثاني أكسيد الكربون",
      "النيتروجين",
      "الأكسجين"
    ],
    "answer": 2
  },
  {
    "id": "SC-12",
    "category": "science",
    "difficulty": 1,
    "question": "أي من هذه الحيوانات برمائي؟",
    "options": [
      "الضفدع",
      "السلحفاة",
      "التمساح",
      "السمكة"
    ],
    "answer": 0
  },
  {
    "id": "SC-13",
    "category": "science",
    "difficulty": 1,
    "question": "ما الجزء من النبات الذي يمتص الماء من التربة؟",
    "options": [
      "الأوراق",
      "الأزهار",
      "الساق",
      "الجذور"
    ],
    "answer": 3
  },
  {
    "id": "SC-14",
    "category": "science",
    "difficulty": 1,
    "question": "كم درجة غليان الماء عند مستوى سطح البحر؟",
    "options": [
      "50 درجة مئوية",
      "90 درجة مئوية",
      "100 درجة مئوية",
      "120 درجة مئوية"
    ],
    "answer": 2
  },
  {
    "id": "SC-15",
    "category": "science",
    "difficulty": 1,
    "question": "كم درجة تجمد الماء؟",
    "options": [
      "10 درجات مئوية",
      "−10 درجات مئوية",
      "صفر درجة مئوية",
      "4 درجات مئوية"
    ],
    "answer": 2
  },
  {
    "id": "SC-16",
    "category": "science",
    "difficulty": 1,
    "question": "ما القوة التي تجذب الأجسام نحو الأرض؟",
    "options": [
      "المغناطيسية",
      "الاحتكاك",
      "الجاذبية",
      "الطفو"
    ],
    "answer": 2
  },
  {
    "id": "SC-17",
    "category": "science",
    "difficulty": 2,
    "question": "ما أصغر وحدة في العنصر الكيميائي تحتفظ بخواصه؟",
    "options": [
      "الإلكترون",
      "الجزيء",
      "الذرة",
      "الخلية"
    ],
    "answer": 2
  },
  {
    "id": "SC-18",
    "category": "science",
    "difficulty": 2,
    "question": "ما الجسيم ذو الشحنة السالبة في الذرة؟",
    "options": [
      "النيوترون",
      "الإلكترون",
      "النواة",
      "البروتون"
    ],
    "answer": 1
  },
  {
    "id": "SC-19",
    "category": "science",
    "difficulty": 2,
    "question": "ما الجسيم ذو الشحنة الموجبة في الذرة؟",
    "options": [
      "الفوتون",
      "الإلكترون",
      "النيوترون",
      "البروتون"
    ],
    "answer": 3
  },
  {
    "id": "SC-20",
    "category": "science",
    "difficulty": 2,
    "question": "كم عدد عظام جسم الإنسان البالغ؟",
    "options": [
      "226 عظمة",
      "206 عظمات",
      "250 عظمة",
      "186 عظمة"
    ],
    "answer": 1
  },
  {
    "id": "SC-21",
    "category": "science",
    "difficulty": 2,
    "question": "ما المعدن الوحيد السائل في درجة حرارة الغرفة؟",
    "options": [
      "الألومنيوم",
      "القصدير",
      "الرصاص",
      "الزئبق"
    ],
    "answer": 3
  },
  {
    "id": "SC-22",
    "category": "science",
    "difficulty": 1,
    "question": "ما العملية التي يصنع بها النبات غذاءه؟",
    "options": [
      "التنفس",
      "النتح",
      "الإخصاب",
      "البناء الضوئي"
    ],
    "answer": 3
  },
  {
    "id": "SC-23",
    "category": "science",
    "difficulty": 1,
    "question": "ما الغاز الذي تطلقه النباتات في البناء الضوئي؟",
    "options": [
      "الأكسجين",
      "الميثان",
      "النيتروجين",
      "ثاني أكسيد الكربون"
    ],
    "answer": 0
  },
  {
    "id": "SC-24",
    "category": "science",
    "difficulty": 2,
    "question": "ما الكوكب صاحب الحلقات الأكثر وضوحًا؟",
    "options": [
      "المشتري",
      "أورانوس",
      "زحل",
      "نبتون"
    ],
    "answer": 2
  },
  {
    "id": "SC-25",
    "category": "science",
    "difficulty": 1,
    "question": "ما أقرب نجم إلى الأرض؟",
    "options": [
      "نجم سهيل",
      "الشمس",
      "النجم القطبي",
      "نجم الشعرى"
    ],
    "answer": 1
  },
  {
    "id": "SC-26",
    "category": "science",
    "difficulty": 1,
    "question": "ماذا يقيس الترمومتر؟",
    "options": [
      "الرطوبة",
      "الضغط الجوي",
      "درجة الحرارة",
      "سرعة الرياح"
    ],
    "answer": 2
  },
  {
    "id": "SC-27",
    "category": "science",
    "difficulty": 3,
    "question": "ماذا يقيس البارومتر؟",
    "options": [
      "سرعة الرياح",
      "الضغط الجوي",
      "درجة الحرارة",
      "كمية الأمطار"
    ],
    "answer": 1
  },
  {
    "id": "SC-28",
    "category": "science",
    "difficulty": 2,
    "question": "كم عدد حجرات قلب الإنسان؟",
    "options": [
      "5 حجرات",
      "حجرتان",
      "3 حجرات",
      "4 حجرات"
    ],
    "answer": 3
  },
  {
    "id": "SC-29",
    "category": "science",
    "difficulty": 2,
    "question": "ما خلايا الدم التي تدافع عن الجسم ضد الأمراض؟",
    "options": [
      "خلايا الدم البيضاء",
      "البلازما",
      "الصفائح الدموية",
      "خلايا الدم الحمراء"
    ],
    "answer": 0
  },
  {
    "id": "SC-30",
    "category": "science",
    "difficulty": 2,
    "question": "ما الفيتامين الذي يصنعه الجلد عند التعرض للشمس؟",
    "options": [
      "فيتامين أ",
      "فيتامين ب12",
      "فيتامين ج",
      "فيتامين د"
    ],
    "answer": 3
  },
  {
    "id": "SC-31",
    "category": "science",
    "difficulty": 3,
    "question": "نقص أي فيتامين يسبب مرض الإسقربوط؟",
    "options": [
      "فيتامين د",
      "فيتامين ج",
      "فيتامين ك",
      "فيتامين أ"
    ],
    "answer": 1
  },
  {
    "id": "SC-32",
    "category": "science",
    "difficulty": 1,
    "question": "كم عدد أرجل الحشرة؟",
    "options": [
      "10 أرجل",
      "4 أرجل",
      "8 أرجل",
      "6 أرجل"
    ],
    "answer": 3
  },
  {
    "id": "SC-33",
    "category": "science",
    "difficulty": 1,
    "question": "كم عدد أرجل العنكبوت؟",
    "options": [
      "6 أرجل",
      "10 أرجل",
      "12 رجلًا",
      "8 أرجل"
    ],
    "answer": 3
  },
  {
    "id": "SC-34",
    "category": "science",
    "difficulty": 2,
    "question": "ما الثديي الوحيد القادر على الطيران الحقيقي؟",
    "options": [
      "الطائر الطنان",
      "الليمور",
      "الخفاش",
      "السنجاب الطائر"
    ],
    "answer": 2
  },
  {
    "id": "SC-35",
    "category": "science",
    "difficulty": 1,
    "question": "ما أكبر طائر في العالم؟",
    "options": [
      "النعامة",
      "البطريق",
      "البجع",
      "النسر"
    ],
    "answer": 0
  },
  {
    "id": "SC-36",
    "category": "science",
    "difficulty": 1,
    "question": "ما حالة المادة التي لها شكل وحجم ثابتان؟",
    "options": [
      "الحالة الصلبة",
      "الحالة الغازية",
      "البلازما",
      "الحالة السائلة"
    ],
    "answer": 0
  },
  {
    "id": "SC-37",
    "category": "science",
    "difficulty": 1,
    "question": "ما تحول المادة من سائل إلى غاز؟",
    "options": [
      "التكاثف",
      "التجمد",
      "الانصهار",
      "التبخر"
    ],
    "answer": 3
  },
  {
    "id": "SC-38",
    "category": "science",
    "difficulty": 2,
    "question": "ما تحول المادة من غاز إلى سائل؟",
    "options": [
      "التكاثف",
      "التسامي",
      "الانصهار",
      "التبخر"
    ],
    "answer": 0
  },
  {
    "id": "SC-39",
    "category": "science",
    "difficulty": 2,
    "question": "ما وحدة قياس القوة؟",
    "options": [
      "الجول",
      "الواط",
      "النيوتن",
      "الأمبير"
    ],
    "answer": 2
  },
  {
    "id": "SC-40",
    "category": "science",
    "difficulty": 2,
    "question": "ما وحدة قياس شدة التيار الكهربائي؟",
    "options": [
      "الفولت",
      "الأوم",
      "الأمبير",
      "الواط"
    ],
    "answer": 2
  },
  {
    "id": "SP-01",
    "category": "sports",
    "difficulty": 1,
    "question": "كم عدد لاعبي فريق كرة القدم في الملعب؟",
    "options": [
      "12 لاعبًا",
      "9 لاعبين",
      "11 لاعبًا",
      "10 لاعبين"
    ],
    "answer": 2
  },
  {
    "id": "SP-02",
    "category": "sports",
    "difficulty": 1,
    "question": "كم مدة مباراة كرة القدم النظامية؟",
    "options": [
      "60 دقيقة",
      "80 دقيقة",
      "90 دقيقة",
      "100 دقيقة"
    ],
    "answer": 2
  },
  {
    "id": "SP-03",
    "category": "sports",
    "difficulty": 1,
    "question": "كم عدد لاعبي فريق كرة السلة في الملعب؟",
    "options": [
      "6 لاعبين",
      "7 لاعبين",
      "5 لاعبين",
      "4 لاعبين"
    ],
    "answer": 2
  },
  {
    "id": "SP-04",
    "category": "sports",
    "difficulty": 2,
    "question": "في أي رياضة تُقام بطولة ويمبلدون؟",
    "options": [
      "كرة الطاولة",
      "الريشة الطائرة",
      "التنس",
      "الجولف"
    ],
    "answer": 2
  },
  {
    "id": "SP-05",
    "category": "sports",
    "difficulty": 1,
    "question": "كم نقطة تُحتسب للرمية الحرة في كرة السلة؟",
    "options": [
      "نقطة واحدة",
      "نقطتان",
      "4 نقاط",
      "3 نقاط"
    ],
    "answer": 0
  },
  {
    "id": "SP-06",
    "category": "sports",
    "difficulty": 1,
    "question": "كم نقطة للتسديدة من خارج القوس في كرة السلة؟",
    "options": [
      "3 نقاط",
      "نقطة واحدة",
      "نقطتان",
      "4 نقاط"
    ],
    "answer": 0
  },
  {
    "id": "SP-07",
    "category": "sports",
    "difficulty": 2,
    "question": "كم عدد لاعبي فريق الكرة الطائرة في الملعب؟",
    "options": [
      "7 لاعبين",
      "5 لاعبين",
      "8 لاعبين",
      "6 لاعبين"
    ],
    "answer": 3
  },
  {
    "id": "SP-08",
    "category": "sports",
    "difficulty": 3,
    "question": "كم شوطًا يحتاج الفريق للفوز بمباراة الكرة الطائرة (من 5 أشواط)؟",
    "options": [
      "4 أشواط",
      "شوطان",
      "5 أشواط",
      "3 أشواط"
    ],
    "answer": 3
  },
  {
    "id": "SP-09",
    "category": "sports",
    "difficulty": 1,
    "question": "ما الدولة التي استضافت كأس العالم 2022؟",
    "options": [
      "قطر",
      "الإمارات",
      "البحرين",
      "السعودية"
    ],
    "answer": 0
  },
  {
    "id": "SP-10",
    "category": "sports",
    "difficulty": 1,
    "question": "ما المنتخب الذي فاز بكأس العالم 2022؟",
    "options": [
      "البرازيل",
      "فرنسا",
      "الأرجنتين",
      "كرواتيا"
    ],
    "answer": 2
  },
  {
    "id": "SP-11",
    "category": "sports",
    "difficulty": 2,
    "question": "ما المنتخب الذي فاز بكأس العالم 2018؟",
    "options": [
      "بلجيكا",
      "فرنسا",
      "إنجلترا",
      "كرواتيا"
    ],
    "answer": 1
  },
  {
    "id": "SP-12",
    "category": "sports",
    "difficulty": 2,
    "question": "ما المنتخب الأكثر تتويجًا بكأس العالم؟",
    "options": [
      "الأرجنتين",
      "إيطاليا",
      "ألمانيا",
      "البرازيل"
    ],
    "answer": 3
  },
  {
    "id": "SP-13",
    "category": "sports",
    "difficulty": 2,
    "question": "كم مرة فازت البرازيل بكأس العالم؟",
    "options": [
      "6 مرات",
      "3 مرات",
      "5 مرات",
      "4 مرات"
    ],
    "answer": 2
  },
  {
    "id": "SP-14",
    "category": "sports",
    "difficulty": 1,
    "question": "ما الرياضة الملقبة بـ«الساحرة المستديرة»؟",
    "options": [
      "كرة القدم",
      "كرة اليد",
      "كرة السلة",
      "التنس"
    ],
    "answer": 0
  },
  {
    "id": "SP-15",
    "category": "sports",
    "difficulty": 3,
    "question": "كم عدد الحفر في جولة الجولف القياسية؟",
    "options": [
      "9 حفر",
      "18 حفرة",
      "12 حفرة",
      "24 حفرة"
    ],
    "answer": 1
  },
  {
    "id": "SP-16",
    "category": "sports",
    "difficulty": 2,
    "question": "ما طول المسبح الأولمبي القياسي؟",
    "options": [
      "25 مترًا",
      "75 مترًا",
      "100 متر",
      "50 مترًا"
    ],
    "answer": 3
  },
  {
    "id": "SP-17",
    "category": "sports",
    "difficulty": 1,
    "question": "كم عدد الحلقات في شعار الأولمبياد؟",
    "options": [
      "7 حلقات",
      "6 حلقات",
      "4 حلقات",
      "5 حلقات"
    ],
    "answer": 3
  },
  {
    "id": "SP-18",
    "category": "sports",
    "difficulty": 1,
    "question": "كل كم سنة تُقام الألعاب الأولمبية الصيفية؟",
    "options": [
      "كل 4 سنوات",
      "كل 5 سنوات",
      "كل سنتين",
      "كل 3 سنوات"
    ],
    "answer": 0
  },
  {
    "id": "SP-19",
    "category": "sports",
    "difficulty": 1,
    "question": "ما الرياضة التي تستخدم الريشة الطائرة؟",
    "options": [
      "كرة الطاولة",
      "الإسكواش",
      "التنس",
      "الريشة الطائرة (بادمنتون)"
    ],
    "answer": 3
  },
  {
    "id": "SP-20",
    "category": "sports",
    "difficulty": 2,
    "question": "كم عدد لاعبي فريق كرة اليد في الملعب؟",
    "options": [
      "6 لاعبين",
      "8 لاعبين",
      "7 لاعبين",
      "5 لاعبين"
    ],
    "answer": 2
  },
  {
    "id": "SP-21",
    "category": "sports",
    "difficulty": 2,
    "question": "كم مدة مباراة كرة اليد النظامية؟",
    "options": [
      "60 دقيقة",
      "90 دقيقة",
      "45 دقيقة",
      "70 دقيقة"
    ],
    "answer": 0
  },
  {
    "id": "SP-22",
    "category": "sports",
    "difficulty": 2,
    "question": "في أي رياضة اشتهر محمد علي كلاي؟",
    "options": [
      "الجودو",
      "الكاراتيه",
      "المصارعة",
      "الملاكمة"
    ],
    "answer": 3
  },
  {
    "id": "SP-23",
    "category": "sports",
    "difficulty": 3,
    "question": "كم عدد الجولات القصوى في نزال الملاكمة المحترف؟",
    "options": [
      "12 جولة",
      "15 جولة",
      "8 جولات",
      "10 جولات"
    ],
    "answer": 0
  },
  {
    "id": "SP-24",
    "category": "sports",
    "difficulty": 2,
    "question": "في أي دولة نشأت رياضة الجودو؟",
    "options": [
      "اليابان",
      "الصين",
      "كوريا الجنوبية",
      "تايلاند"
    ],
    "answer": 0
  },
  {
    "id": "SP-25",
    "category": "sports",
    "difficulty": 2,
    "question": "ما الرياضة الوطنية التقليدية في اليابان؟",
    "options": [
      "الكندو",
      "الجودو",
      "الكاراتيه",
      "السومو"
    ],
    "answer": 3
  },
  {
    "id": "SP-26",
    "category": "sports",
    "difficulty": 2,
    "question": "كم عدد لاعبي فريق كرة الصالات (فوتسال)؟",
    "options": [
      "6 لاعبين",
      "4 لاعبين",
      "5 لاعبين",
      "7 لاعبين"
    ],
    "answer": 2
  },
  {
    "id": "SP-27",
    "category": "sports",
    "difficulty": 1,
    "question": "ما لون البطاقة التي تعني الطرد في كرة القدم؟",
    "options": [
      "الأزرق",
      "الأصفر",
      "الأحمر",
      "الأخضر"
    ],
    "answer": 2
  },
  {
    "id": "SP-28",
    "category": "sports",
    "difficulty": 1,
    "question": "ماذا تعني البطاقة الصفراء في كرة القدم؟",
    "options": [
      "ركلة جزاء",
      "إنذار",
      "هدف",
      "طرد"
    ],
    "answer": 1
  },
  {
    "id": "SP-29",
    "category": "sports",
    "difficulty": 2,
    "question": "ما مسافة سباق الماراثون التقريبية؟",
    "options": [
      "42 كم",
      "35 كم",
      "21 كم",
      "50 كم"
    ],
    "answer": 0
  },
  {
    "id": "SP-30",
    "category": "sports",
    "difficulty": 1,
    "question": "في أي رياضة يُستخدم مصطلح «سلام دانك»؟",
    "options": [
      "كرة السلة",
      "التنس",
      "كرة الطائرة",
      "كرة اليد"
    ],
    "answer": 0
  },
  {
    "id": "SP-31",
    "category": "sports",
    "difficulty": 3,
    "question": "كم نقطة للتاتش داون في كرة القدم الأمريكية؟",
    "options": [
      "2 نقطتان",
      "6 نقاط",
      "7 نقاط",
      "3 نقاط"
    ],
    "answer": 1
  },
  {
    "id": "SP-32",
    "category": "sports",
    "difficulty": 2,
    "question": "في أي رياضة يُستخدم مصطلحا «love» و«deuce»؟",
    "options": [
      "الريشة الطائرة",
      "الجولف",
      "الإسكواش",
      "التنس"
    ],
    "answer": 3
  },
  {
    "id": "SP-33",
    "category": "sports",
    "difficulty": 3,
    "question": "كم عدد لاعبي فريق هوكي الجليد على الجليد؟",
    "options": [
      "5 لاعبين",
      "8 لاعبين",
      "6 لاعبين",
      "7 لاعبين"
    ],
    "answer": 2
  },
  {
    "id": "SP-34",
    "category": "sports",
    "difficulty": 2,
    "question": "ما أول دولة أفريقية تستضيف كأس العالم؟",
    "options": [
      "مصر",
      "جنوب أفريقيا",
      "نيجيريا",
      "المغرب"
    ],
    "answer": 1
  },
  {
    "id": "SP-35",
    "category": "sports",
    "difficulty": 2,
    "question": "ما المنتخب الذي فاز بكأس العالم 2010؟",
    "options": [
      "إسبانيا",
      "ألمانيا",
      "هولندا",
      "الأوروغواي"
    ],
    "answer": 0
  },
  {
    "id": "SP-36",
    "category": "sports",
    "difficulty": 1,
    "question": "ما النادي الملقب بـ«الملكي»؟",
    "options": [
      "بايرن ميونخ",
      "برشلونة",
      "ريال مدريد",
      "مانشستر يونايتد"
    ],
    "answer": 2
  },
  {
    "id": "SP-37",
    "category": "sports",
    "difficulty": 2,
    "question": "ما النادي الملقب بـ«البلوغرانا»؟",
    "options": [
      "برشلونة",
      "ريال مدريد",
      "أتلتيكو مدريد",
      "إشبيلية"
    ],
    "answer": 0
  },
  {
    "id": "SP-38",
    "category": "sports",
    "difficulty": 3,
    "question": "ما أعلى بريكة ممكنة في سنوكر المحترف؟",
    "options": [
      "147",
      "140",
      "150",
      "155"
    ],
    "answer": 0
  },
  {
    "id": "SP-39",
    "category": "sports",
    "difficulty": 2,
    "question": "كم عدد بطولات الجراند سلام في التنس سنويًا؟",
    "options": [
      "6 بطولات",
      "5 بطولات",
      "4 بطولات",
      "3 بطولات"
    ],
    "answer": 2
  },
  {
    "id": "SP-40",
    "category": "sports",
    "difficulty": 2,
    "question": "في أي دولة نشأت رياضة التايكوندو؟",
    "options": [
      "اليابان",
      "كوريا الجنوبية",
      "تايلاند",
      "الصين"
    ],
    "answer": 1
  },
  {
    "id": "TE-01",
    "category": "tech",
    "difficulty": 1,
    "question": "ماذا تعني CPU بالعربية؟",
    "options": [
      "وحدة التحكم بالشبكة",
      "وحدة عرض الرسوميات",
      "وحدة المعالجة المركزية",
      "وحدة تخزين البيانات"
    ],
    "answer": 2
  },
  {
    "id": "TE-02",
    "category": "tech",
    "difficulty": 2,
    "question": "ماذا تعني RAM؟",
    "options": [
      "ذاكرة الوصول العشوائي",
      "القرص الصلب",
      "ذاكرة التخزين الدائم",
      "ذاكرة القراءة فقط"
    ],
    "answer": 0
  },
  {
    "id": "TE-03",
    "category": "tech",
    "difficulty": 1,
    "question": "ما الذاكرة التي تفقد بياناتها عند انقطاع الكهرباء؟",
    "options": [
      "الفلاشة",
      "ROM",
      "القرص الصلب SSD",
      "RAM"
    ],
    "answer": 3
  },
  {
    "id": "TE-04",
    "category": "tech",
    "difficulty": 2,
    "question": "أي من هذه وسائط تخزين دائمة؟",
    "options": [
      "القرص SSD",
      "RAM",
      "سجل المعالج",
      "ذاكرة الكاش"
    ],
    "answer": 0
  },
  {
    "id": "TE-05",
    "category": "tech",
    "difficulty": 1,
    "question": "ما الشركة المصنعة لهاتف iPhone؟",
    "options": [
      "Huawei",
      "Apple",
      "Samsung",
      "Google"
    ],
    "answer": 1
  },
  {
    "id": "TE-06",
    "category": "tech",
    "difficulty": 1,
    "question": "ما الشركة التي تطور نظام Android؟",
    "options": [
      "Microsoft",
      "Google",
      "Nokia",
      "Apple"
    ],
    "answer": 1
  },
  {
    "id": "TE-07",
    "category": "tech",
    "difficulty": 1,
    "question": "ما لغة البرمجة المسماة على اسم ثعبان؟",
    "options": [
      "Ruby",
      "C++",
      "Python",
      "Java"
    ],
    "answer": 2
  },
  {
    "id": "TE-08",
    "category": "tech",
    "difficulty": 1,
    "question": "ما اللغة المستخدمة لبناء هيكل صفحات الويب؟",
    "options": [
      "SQL",
      "HTML",
      "Python",
      "CSS"
    ],
    "answer": 1
  },
  {
    "id": "TE-09",
    "category": "tech",
    "difficulty": 1,
    "question": "ما اللغة المستخدمة لتنسيق صفحات الويب وألوانها؟",
    "options": [
      "JavaScript",
      "HTML",
      "PHP",
      "CSS"
    ],
    "answer": 3
  },
  {
    "id": "TE-10",
    "category": "tech",
    "difficulty": 1,
    "question": "ماذا يعني اختصار AI؟",
    "options": [
      "الأتمتة الصناعية",
      "التحليل الرقمي",
      "الإنترنت المتقدم",
      "الذكاء الاصطناعي"
    ],
    "answer": 3
  },
  {
    "id": "TE-11",
    "category": "tech",
    "difficulty": 2,
    "question": "ماذا يعني اختصار ML؟",
    "options": [
      "المنطق الرياضي",
      "ذاكرة الوصول",
      "لغة الترميز",
      "تعلم الآلة"
    ],
    "answer": 3
  },
  {
    "id": "TE-12",
    "category": "tech",
    "difficulty": 1,
    "question": "ما الشركة التي طورت ChatGPT؟",
    "options": [
      "Google",
      "OpenAI",
      "Meta",
      "Microsoft"
    ],
    "answer": 1
  },
  {
    "id": "TE-13",
    "category": "tech",
    "difficulty": 2,
    "question": "ماذا تعني GPU؟",
    "options": [
      "وحدة التخزين العامة",
      "وحدة المعالجة المركزية",
      "وحدة معالجة الرسوميات",
      "بوابة الشبكة"
    ],
    "answer": 2
  },
  {
    "id": "TE-14",
    "category": "tech",
    "difficulty": 1,
    "question": "كم عدد البتات في البايت الواحد؟",
    "options": [
      "8 بتات",
      "16 بتًا",
      "10 بتات",
      "4 بتات"
    ],
    "answer": 0
  },
  {
    "id": "TE-15",
    "category": "tech",
    "difficulty": 2,
    "question": "كم بايت في الكيلوبايت الواحد (النظام الثنائي)؟",
    "options": [
      "1024 بايت",
      "1000 بايت",
      "512 بايت",
      "2048 بايت"
    ],
    "answer": 0
  },
  {
    "id": "TE-16",
    "category": "tech",
    "difficulty": 1,
    "question": "ماذا يعني اختصار WWW؟",
    "options": [
      "الشبكة العنكبوتية العالمية",
      "واجهة الويب الحديثة",
      "نظام التشغيل الواسع",
      "بروتوكول نقل الملفات"
    ],
    "answer": 0
  },
  {
    "id": "TE-17",
    "category": "tech",
    "difficulty": 2,
    "question": "ما البروتوكول الآمن لتصفح المواقع؟",
    "options": [
      "FTP",
      "HTTPS",
      "SMTP",
      "HTTP"
    ],
    "answer": 1
  },
  {
    "id": "TE-18",
    "category": "tech",
    "difficulty": 3,
    "question": "ما المنفذ الافتراضي لبروتوكول HTTP؟",
    "options": [
      "80",
      "21",
      "443",
      "8080"
    ],
    "answer": 0
  },
  {
    "id": "TE-19",
    "category": "tech",
    "difficulty": 2,
    "question": "ماذا يعني اختصار USB؟",
    "options": [
      "نظام التشغيل الموحد",
      "الناقل التسلسلي العام",
      "وحدة التخزين السريعة",
      "منفذ الشاشة الرقمي"
    ],
    "answer": 1
  },
  {
    "id": "TE-20",
    "category": "tech",
    "difficulty": 1,
    "question": "ما الشركة المصنعة لنظام Windows؟",
    "options": [
      "Oracle",
      "Microsoft",
      "Apple",
      "IBM"
    ],
    "answer": 1
  },
  {
    "id": "TE-21",
    "category": "tech",
    "difficulty": 2,
    "question": "ما نظام التشغيل مفتوح المصدر الذي شعاره بطريق؟",
    "options": [
      "Windows",
      "Linux",
      "macOS",
      "Android"
    ],
    "answer": 1
  },
  {
    "id": "TE-22",
    "category": "tech",
    "difficulty": 2,
    "question": "ما اللغة المستخدمة للاستعلام من قواعد البيانات؟",
    "options": [
      "SQL",
      "XML",
      "HTML",
      "CSS"
    ],
    "answer": 0
  },
  {
    "id": "TE-23",
    "category": "tech",
    "difficulty": 3,
    "question": "ماذا يفعل المترجم (Compiler)؟",
    "options": [
      "يصمم واجهات المواقع",
      "يخزن البيانات في السحابة",
      "يرسل البريد الإلكتروني",
      "يحول الكود المصدري إلى برنامج قابل للتنفيذ"
    ],
    "answer": 3
  },
  {
    "id": "TE-24",
    "category": "tech",
    "difficulty": 1,
    "question": "ما أصغر وحدة بيانات في الحاسوب؟",
    "options": [
      "البايت",
      "البت (Bit)",
      "الميجابايت",
      "الكيلوبايت"
    ],
    "answer": 1
  },
  {
    "id": "TE-25",
    "category": "tech",
    "difficulty": 2,
    "question": "ماذا يعني اختصار IoT؟",
    "options": [
      "إنترنت الأشياء",
      "تقنية الإدخال",
      "إنترنت المؤسسات",
      "شبكة الاتصالات الداخلية"
    ],
    "answer": 0
  },
  {
    "id": "TE-26",
    "category": "tech",
    "difficulty": 1,
    "question": "ما التقنية التي تجعل الآلة تتعلم من البيانات؟",
    "options": [
      "الطباعة ثلاثية الأبعاد",
      "التخزين السحابي",
      "البث المباشر",
      "تعلم الآلة"
    ],
    "answer": 3
  },
  {
    "id": "TE-27",
    "category": "tech",
    "difficulty": 2,
    "question": "ما نوع الذكاء الاصطناعي المستوحى من الدماغ البشري؟",
    "options": [
      "جداول البيانات",
      "أنظمة الملفات",
      "قواعد البيانات",
      "الشبكات العصبية"
    ],
    "answer": 3
  },
  {
    "id": "TE-28",
    "category": "tech",
    "difficulty": 1,
    "question": "ما الشركة المصنعة لبطاقات GeForce؟",
    "options": [
      "NVIDIA",
      "Intel",
      "Qualcomm",
      "AMD"
    ],
    "answer": 0
  },
  {
    "id": "TE-29",
    "category": "tech",
    "difficulty": 1,
    "question": "ماذا يعني FPS في الألعاب؟",
    "options": [
      "عدد الإطارات في الثانية",
      "سرعة الإنترنت",
      "دقة الشاشة",
      "زمن الاستجابة"
    ],
    "answer": 0
  },
  {
    "id": "TE-30",
    "category": "tech",
    "difficulty": 2,
    "question": "ماذا يعني اختصار VR؟",
    "options": [
      "الواقع المعزز",
      "البث المباشر",
      "الرؤية الليلية",
      "الواقع الافتراضي"
    ],
    "answer": 3
  },
  {
    "id": "TE-31",
    "category": "tech",
    "difficulty": 2,
    "question": "ماذا يعني اختصار AR؟",
    "options": [
      "الروبوتات المتقدمة",
      "الواقع الافتراضي",
      "الذكاء الاصطناعي",
      "الواقع المعزز"
    ],
    "answer": 3
  },
  {
    "id": "TE-32",
    "category": "tech",
    "difficulty": 1,
    "question": "ماذا يفعل الراوتر في الشبكة؟",
    "options": [
      "يطبع المستندات",
      "يخزن ملفات المستخدمين",
      "يربط الشبكات ويوجه البيانات بينها",
      "يعرض صفحات الويب"
    ],
    "answer": 2
  },
  {
    "id": "TE-33",
    "category": "tech",
    "difficulty": 3,
    "question": "ماذا يفعل نظام DNS؟",
    "options": [
      "يحمي الجهاز من الفيروسات",
      "يضغط الملفات",
      "يحول أسماء النطاقات إلى عناوين IP",
      "يزيد سرعة المعالج"
    ],
    "answer": 2
  },
  {
    "id": "TE-34",
    "category": "tech",
    "difficulty": 2,
    "question": "ماذا يفعل الجدار الناري (Firewall)؟",
    "options": [
      "يعرض الإعلانات",
      "يخزن كلمات المرور",
      "يزيد سرعة الإنترنت",
      "يحمي الشبكة من الوصول غير المصرح به"
    ],
    "answer": 3
  },
  {
    "id": "TE-35",
    "category": "tech",
    "difficulty": 1,
    "question": "كم عدد قنوات الألوان في نموذج RGB؟",
    "options": [
      "قناتان",
      "5 قنوات",
      "3 قنوات",
      "4 قنوات"
    ],
    "answer": 2
  },
  {
    "id": "TE-36",
    "category": "tech",
    "difficulty": 1,
    "question": "ما امتداد ملفات لغة Python؟",
    "options": [
      "css.",
      "js.",
      "html.",
      "py."
    ],
    "answer": 3
  },
  {
    "id": "TE-37",
    "category": "tech",
    "difficulty": 2,
    "question": "ماذا يعني اختصار API؟",
    "options": [
      "واجهة برمجة التطبيقات",
      "بروتوكول نقل آمن",
      "برنامج إدارة الإنترنت",
      "أداة اختبار الأداء"
    ],
    "answer": 0
  },
  {
    "id": "TE-38",
    "category": "tech",
    "difficulty": 1,
    "question": "ما الخوارزمية في البرمجة؟",
    "options": [
      "نوع من الحواسيب",
      "شاشة عرض خاصة",
      "خطوات محددة لحل مشكلة",
      "لغة برمجة قديمة"
    ],
    "answer": 2
  },
  {
    "id": "TE-39",
    "category": "tech",
    "difficulty": 1,
    "question": "ما المتغير في البرمجة؟",
    "options": [
      "نوع من الطابعات",
      "مكان لتخزين قيمة يمكن تغييرها",
      "شاشة الإدخال",
      "ملف صور ثابت"
    ],
    "answer": 1
  },
  {
    "id": "TE-40",
    "category": "tech",
    "difficulty": 1,
    "question": "ماذا يفعل التكرار (Loop) في البرمجة؟",
    "options": [
      "يحذف الملفات",
      "يغلق البرنامج",
      "يطبع ورقة واحدة",
      "يكرر تنفيذ كود عدة مرات"
    ],
    "answer": 3
  },
  {
    "id": "IS-01",
    "category": "islamic",
    "difficulty": 1,
    "question": "كم عدد أركان الإسلام؟",
    "options": [
      "4 أركان",
      "6 أركان",
      "5 أركان",
      "7 أركان"
    ],
    "answer": 2
  },
  {
    "id": "IS-02",
    "category": "islamic",
    "difficulty": 1,
    "question": "كم عدد أركان الإيمان؟",
    "options": [
      "4 أركان",
      "6 أركان",
      "5 أركان",
      "7 أركان"
    ],
    "answer": 1
  },
  {
    "id": "IS-03",
    "category": "islamic",
    "difficulty": 1,
    "question": "كم عدد سور القرآن الكريم؟",
    "options": [
      "100 سورة",
      "114 سورة",
      "120 سورة",
      "110 سور"
    ],
    "answer": 1
  },
  {
    "id": "IS-04",
    "category": "islamic",
    "difficulty": 1,
    "question": "ما أطول سورة في القرآن الكريم؟",
    "options": [
      "سورة آل عمران",
      "سورة النساء",
      "سورة البقرة",
      "سورة المائدة"
    ],
    "answer": 2
  },
  {
    "id": "IS-05",
    "category": "islamic",
    "difficulty": 1,
    "question": "ما أقصر سورة في القرآن الكريم؟",
    "options": [
      "سورة الناس",
      "سورة الكوثر",
      "سورة الفلق",
      "سورة الإخلاص"
    ],
    "answer": 1
  },
  {
    "id": "IS-06",
    "category": "islamic",
    "difficulty": 1,
    "question": "ما أول سورة في المصحف؟",
    "options": [
      "سورة البقرة",
      "سورة الإخلاص",
      "سورة الفاتحة",
      "سورة الناس"
    ],
    "answer": 2
  },
  {
    "id": "IS-07",
    "category": "islamic",
    "difficulty": 2,
    "question": "كم عدد آيات سورة الفاتحة؟",
    "options": [
      "6 آيات",
      "8 آيات",
      "7 آيات",
      "5 آيات"
    ],
    "answer": 2
  },
  {
    "id": "IS-08",
    "category": "islamic",
    "difficulty": 1,
    "question": "كم عدد الصلوات المفروضة في اليوم والليلة؟",
    "options": [
      "4 صلوات",
      "5 صلوات",
      "3 صلوات",
      "6 صلوات"
    ],
    "answer": 1
  },
  {
    "id": "IS-09",
    "category": "islamic",
    "difficulty": 1,
    "question": "كم عدد ركعات صلاة الفجر المفروضة؟",
    "options": [
      "3 ركعات",
      "ركعتان",
      "ركعة واحدة",
      "4 ركعات"
    ],
    "answer": 1
  },
  {
    "id": "IS-10",
    "category": "islamic",
    "difficulty": 1,
    "question": "كم عدد ركعات صلاة المغرب المفروضة؟",
    "options": [
      "ركعتان",
      "3 ركعات",
      "5 ركعات",
      "4 ركعات"
    ],
    "answer": 1
  },
  {
    "id": "IS-11",
    "category": "islamic",
    "difficulty": 1,
    "question": "كم عدد ركعات صلاة الظهر المفروضة؟",
    "options": [
      "3 ركعات",
      "4 ركعات",
      "ركعتان",
      "5 ركعات"
    ],
    "answer": 1
  },
  {
    "id": "IS-12",
    "category": "islamic",
    "difficulty": 1,
    "question": "ما شهر الصيام عند المسلمين؟",
    "options": [
      "رمضان",
      "شوال",
      "ذو القعدة",
      "شعبان"
    ],
    "answer": 0
  },
  {
    "id": "IS-13",
    "category": "islamic",
    "difficulty": 2,
    "question": "ما الليلة التي هي خير من ألف شهر؟",
    "options": [
      "ليلة القدر",
      "ليلة الإسراء",
      "ليلة العيد",
      "ليلة النصف من شعبان"
    ],
    "answer": 0
  },
  {
    "id": "IS-14",
    "category": "islamic",
    "difficulty": 1,
    "question": "ما قبلة المسلمين في الصلاة؟",
    "options": [
      "المسجد الأقصى",
      "الكعبة المشرفة",
      "جبل عرفات",
      "قبة الصخرة"
    ],
    "answer": 1
  },
  {
    "id": "IS-15",
    "category": "islamic",
    "difficulty": 1,
    "question": "إلى أي مدينة هاجر النبي ﷺ؟",
    "options": [
      "مكة المكرمة",
      "الطائف",
      "المدينة المنورة",
      "القدس"
    ],
    "answer": 2
  },
  {
    "id": "IS-16",
    "category": "islamic",
    "difficulty": 1,
    "question": "في أي مدينة وُلد النبي ﷺ؟",
    "options": [
      "الطائف",
      "المدينة المنورة",
      "مكة المكرمة",
      "بدر"
    ],
    "answer": 2
  },
  {
    "id": "IS-17",
    "category": "islamic",
    "difficulty": 2,
    "question": "ما اسم والد النبي ﷺ؟",
    "options": [
      "عبدالمناف",
      "أبو طالب",
      "عبدالله",
      "عبدالمطلب"
    ],
    "answer": 2
  },
  {
    "id": "IS-18",
    "category": "islamic",
    "difficulty": 2,
    "question": "ما اسم والدة النبي ﷺ؟",
    "options": [
      "خديجة بنت خويلد",
      "حليمة السعدية",
      "آمنة بنت وهب",
      "فاطمة بنت أسد"
    ],
    "answer": 2
  },
  {
    "id": "IS-19",
    "category": "islamic",
    "difficulty": 1,
    "question": "من أول الخلفاء الراشدين؟",
    "options": [
      "أبو بكر الصديق",
      "علي بن أبي طالب",
      "عمر بن الخطاب",
      "عثمان بن عفان"
    ],
    "answer": 0
  },
  {
    "id": "IS-20",
    "category": "islamic",
    "difficulty": 2,
    "question": "من الخليفة الملقب بالفاروق؟",
    "options": [
      "علي بن أبي طالب",
      "أبو بكر الصديق",
      "عمر بن الخطاب",
      "عثمان بن عفان"
    ],
    "answer": 2
  },
  {
    "id": "IS-21",
    "category": "islamic",
    "difficulty": 2,
    "question": "من الصحابي الملقب بسيف الله المسلول؟",
    "options": [
      "خالد بن الوليد",
      "أبو عبيدة بن الجراح",
      "عمرو بن العاص",
      "سعد بن أبي وقاص"
    ],
    "answer": 0
  },
  {
    "id": "IS-22",
    "category": "islamic",
    "difficulty": 1,
    "question": "ما الملك الموكل بالوحي؟",
    "options": [
      "إسرافيل",
      "مالك",
      "ميكائيل",
      "جبريل عليه السلام"
    ],
    "answer": 3
  },
  {
    "id": "IS-23",
    "category": "islamic",
    "difficulty": 3,
    "question": "ما الملك الموكل بالنفخ في الصور؟",
    "options": [
      "إسرافيل عليه السلام",
      "ميكائيل",
      "جبريل",
      "عزرائيل"
    ],
    "answer": 0
  },
  {
    "id": "IS-24",
    "category": "islamic",
    "difficulty": 3,
    "question": "كم مرة ذُكر اسم «محمد» صريحًا في القرآن الكريم؟",
    "options": [
      "6 مرات",
      "4 مرات",
      "5 مرات",
      "3 مرات"
    ],
    "answer": 1
  },
  {
    "id": "IS-25",
    "category": "islamic",
    "difficulty": 2,
    "question": "ما السورة الملقبة بقلب القرآن؟",
    "options": [
      "سورة الكهف",
      "سورة يس",
      "سورة الملك",
      "سورة الرحمن"
    ],
    "answer": 1
  },
  {
    "id": "IS-26",
    "category": "islamic",
    "difficulty": 1,
    "question": "ما السورة التي تعدل ثلث القرآن؟",
    "options": [
      "سورة الكوثر",
      "سورة الإخلاص",
      "سورة الفاتحة",
      "سورة الناس"
    ],
    "answer": 1
  },
  {
    "id": "IS-27",
    "category": "islamic",
    "difficulty": 1,
    "question": "كم عدد أجزاء القرآن الكريم؟",
    "options": [
      "40 جزءًا",
      "20 جزءًا",
      "30 جزءًا",
      "60 جزءًا"
    ],
    "answer": 2
  },
  {
    "id": "IS-28",
    "category": "islamic",
    "difficulty": 2,
    "question": "كم عدد أحزاب القرآن الكريم؟",
    "options": [
      "60 حزبًا",
      "30 حزبًا",
      "40 حزبًا",
      "114 حزبًا"
    ],
    "answer": 0
  },
  {
    "id": "IS-29",
    "category": "islamic",
    "difficulty": 2,
    "question": "ما أول مسجد بُني في الإسلام؟",
    "options": [
      "مسجد قباء",
      "المسجد الحرام",
      "المسجد الأقصى",
      "المسجد النبوي"
    ],
    "answer": 0
  },
  {
    "id": "IS-30",
    "category": "islamic",
    "difficulty": 1,
    "question": "أين يقع المسجد النبوي؟",
    "options": [
      "مكة المكرمة",
      "القدس",
      "المدينة المنورة",
      "الطائف"
    ],
    "answer": 2
  },
  {
    "id": "IS-31",
    "category": "islamic",
    "difficulty": 1,
    "question": "ما اسم البئر المباركة قرب الكعبة؟",
    "options": [
      "بئر زمزم",
      "بئر بدر",
      "بئر حراء",
      "بئر أحد"
    ],
    "answer": 0
  },
  {
    "id": "IS-32",
    "category": "islamic",
    "difficulty": 1,
    "question": "ما اسم الجبل الذي يسعى بينه الحجاج مع المروة؟",
    "options": [
      "الصفا",
      "أحد",
      "حراء",
      "عرفات"
    ],
    "answer": 0
  },
  {
    "id": "IS-33",
    "category": "islamic",
    "difficulty": 1,
    "question": "كم عدد أشواط الطواف حول الكعبة؟",
    "options": [
      "10 أشواط",
      "3 أشواط",
      "7 أشواط",
      "5 أشواط"
    ],
    "answer": 2
  },
  {
    "id": "IS-34",
    "category": "islamic",
    "difficulty": 1,
    "question": "ما اليوم الذي تجب فيه صلاة الجمعة؟",
    "options": [
      "يوم الجمعة",
      "يوم الخميس",
      "يوم السبت",
      "يوم الأحد"
    ],
    "answer": 0
  },
  {
    "id": "IS-35",
    "category": "islamic",
    "difficulty": 1,
    "question": "ما العيد الذي يأتي بعد شهر رمضان؟",
    "options": [
      "عيد الفطر",
      "عيد الأضحى",
      "عيد الغدير",
      "عيد المولد"
    ],
    "answer": 0
  },
  {
    "id": "IS-36",
    "category": "islamic",
    "difficulty": 2,
    "question": "كم عدد أيام عيد الأضحى؟",
    "options": [
      "4 أيام",
      "يوم واحد",
      "5 أيام",
      "3 أيام"
    ],
    "answer": 0
  },
  {
    "id": "IS-37",
    "category": "islamic",
    "difficulty": 3,
    "question": "ما اسم ناقة النبي ﷺ؟",
    "options": [
      "الجدعاء",
      "القصواء",
      "العضباء",
      "الشهباء"
    ],
    "answer": 1
  },
  {
    "id": "IS-38",
    "category": "islamic",
    "difficulty": 2,
    "question": "من أكثر الصحابة رواية للحديث؟",
    "options": [
      "أنس بن مالك",
      "ابن عمر",
      "عائشة",
      "أبو هريرة"
    ],
    "answer": 3
  },
  {
    "id": "IS-39",
    "category": "islamic",
    "difficulty": 1,
    "question": "ما أول غزوة انتصر فيها المسلمون؟",
    "options": [
      "غزوة بدر",
      "غزوة أحد",
      "غزوة الخندق",
      "غزوة حنين"
    ],
    "answer": 0
  },
  {
    "id": "IS-40",
    "category": "islamic",
    "difficulty": 3,
    "question": "في أي سنة هجرية توفي النبي ﷺ؟",
    "options": [
      "السنة 13 هـ",
      "السنة 12 هـ",
      "السنة 10 هـ",
      "السنة 11 هـ"
    ],
    "answer": 3
  }
];
