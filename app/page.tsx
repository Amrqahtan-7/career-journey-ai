"use client";
declare global { interface Window { SpeechRecognition: any; webkitSpeechRecognition: any; } }

import { useState, useRef, useEffect, useCallback } from "react";
import {
  SendHorizontal, Moon, Sun, Brain, Loader2, Paperclip, Mic, MicOff,
  ChevronDown, ChevronUp, BarChart2, Users, Briefcase, Globe
} from "lucide-react";

// ─── Types ───────────────────────────────────────────────────────────────────
interface Message {
  sender: "user" | "ai";
  text?: string;
  recommendations?: CareerResult[];
  isLoading?: boolean;
}
interface CareerResult {
  career_title: string;
  tech_field: string;
  estimated_salary: number | null;
  salary_display: string;
  salary_range: string;
  currency: string;
  region: string;
  future_demand: string;
  required_skills: string[];
  skills_you_have: string[];
  skills_to_learn: string[];
  certifications: string[];
  education_required?: string;
  roadmap: string[];
  experience_level: string;
  data_points: number;
  confidence: number;
  description?: string;
  source: string;
  vision_alignment?: {
    vision_label: string; flag: string;
    sector: string; demand: string; growth: string;
  } | null;
}
type DashboardView = "user" | "admin" | "client";
type ConvState = "idle" | "asked_how_are_you";

// ─── Regions ──────────────────────────────────────────────────────────────────
const REGIONS = [
  { value: "UAE",      label: "🇦🇪 UAE",      currency: "AED", vision: "Vision 2030", flag: "🇦🇪" },
  { value: "KSA",      label: "🇸🇦 KSA",      currency: "SAR", vision: "Vision 2030", flag: "🇸🇦" },
  { value: "Pakistan", label: "🇵🇰 Pakistan", currency: "PKR", vision: "Vision 2035", flag: "🇵🇰" },
];

// ─── Language detection ───────────────────────────────────────────────────────
function detectLanguage(text: string): "ar" | "ur" | "en" {
  const arabicPattern = /[\u0600-\u06FF]/;
  const urduPattern = /[\u0600-\u06FF].*[\u06A9\u06AF\u06C1\u06BE\u0679\u0688\u0691\u06BA]/;
  if (urduPattern.test(text)) return "ur";
  if (arabicPattern.test(text)) return "ar";
  return "en";
}

// ─── Small Talk ───────────────────────────────────────────────────────────────
const LANG_REPLIES: Record<string, Record<string, string>> = {
  greeting: {
    en: "Hello! 👋 Great to have you here!\n\nHow are you doing today?",
    ar: "مرحباً! 👋 يسعدني وجودك هنا!\n\nكيف حالك اليوم؟",
    ur: "ہیلو! 👋 آپ کا خیرمقدم ہے!\n\nآج آپ کیسے ہیں؟",
  },
  good: {
    en: "That's wonderful! 😊\n\nI'm always excited to help people find their perfect career. Tell me your interests and I'll find careers matching Vision 2030/2035 for your region!",
    ar: "رائع! 😊\n\nأنا دائماً سعيد بمساعدة الناس في إيجاد مساراتهم المهنية. أخبرني باهتماماتك وسأجد لك المهن المناسبة لرؤية 2030!",
    ur: "بہت اچھا! 😊\n\nمجھے لوگوں کو ان کا بہترین کیریئر تلاش کرنے میں مدد کرنا بہت پسند ہے۔ مجھے اپنی دلچسپیاں بتائیں!",
  },
  bad: {
    en: "I'm sorry to hear that 😔 Sometimes exploring an exciting career path can lift your spirits!\n\nTell me what you love doing and I'll find the best careers for you. 🌟",
    ar: "أنا آسف لسماع ذلك 😔 أحياناً استكشاف مسار مهني مثير يرفع الروح المعنوية!\n\nأخبرني بما تحب وسأجد لك أفضل المهن. 🌟",
    ur: "یہ سن کر افسوس ہوا 😔 کبھی کبھی ایک دلچسپ کیریئر راستہ دریافت کرنا حوصلہ بڑھاتا ہے!\n\nمجھے بتائیں آپ کو کیا پسند ہے۔ 🌟",
  },
  howAreYou: {
    en: "I'm doing fantastic! 🤖✨ Always here to help you discover your perfect career path!\n\nHow about you? Are you doing well?",
    ar: "أنا بخير جداً! 🤖✨ دائماً هنا لمساعدتك في اكتشاف مسارك المهني!\n\nوأنت، كيف حالك؟",
    ur: "میں بہت اچھا ہوں! 🤖✨ ہمیشہ آپ کا بہترین کیریئر راستہ دریافت کرنے میں مدد کے لیے یہاں ہوں!\n\nآپ کیسے ہیں؟",
  },
  thanks: {
    en: "You're very welcome! 😊 If you'd like to explore more careers, just ask! 🚀",
    ar: "على الرحب والسعة! 😊 إذا أردت استكشاف المزيد من المهن، فقط اسأل! 🚀",
    ur: "خوش آمدید! 😊 اگر آپ مزید کیریئرز دریافت کرنا چاہتے ہیں تو بس پوچھیں! 🚀",
  },
  bye: {
    en: "Goodbye! 👋 Best of luck on your career journey! Come back anytime! 🌟",
    ar: "مع السلامة! 👋 بالتوفيق في مسيرتك المهنية! عد إلينا في أي وقت! 🌟",
    ur: "خدا حافظ! 👋 آپ کے کیریئر کے سفر میں بہترین خوش قسمتی! کبھی بھی واپس آئیں! 🌟",
  },
  badWords: {
    en: "I'm sorry if I didn't meet your expectations 😔 I'm always improving! Let me know what went wrong. 💪",
    ar: "أنا آسف إذا لم أكن عند مستوى توقعاتك 😔 أنا دائماً أتحسن! أخبرني بما حدث. 💪",
    ur: "معذرت اگر میں آپ کی توقعات پر پورا نہیں اترا 😔 میں ہمیشہ بہتر ہو رہا ہوں! مجھے بتائیں کیا غلط ہوا۔ 💪",
  },
  confused: {
    en: "No worries! 😊 Just describe anything you enjoy and I'll suggest careers:\n• 'I like drawing'\n• 'I enjoy helping others'\n• 'I love technology'",
    ar: "لا تقلق! 😊 فقط صف أي شيء تستمتع به وسأقترح مهناً:\n• 'أحب الرسم'\n• 'أستمتع بمساعدة الآخرين'\n• 'أحب التكنولوجيا'",
    ur: "کوئی بات نہیں! 😊 بس کچھ بھی بتائیں جو آپ کو پسند ہو:\n• 'مجھے ڈرائنگ پسند ہے'\n• 'میں لوگوں کی مدد کرنا پسند کرتا ہوں'\n• 'مجھے ٹیکنالوجی پسند ہے'",
  },
  whatCanYouDo: {
    en: "Here's what I can do 🚀\n\n• 🔍 Find careers matching your interests\n• 💰 Real salary data in AED/SAR/PKR\n• 🎯 Skills gap analysis\n• 🌍 Vision 2030/2035 alignment\n• 🗺️ Step-by-step roadmap\n• ⚖️ Compare careers side by side\n• 🌐 Arabic, Urdu & English\n• 🎤 Voice input\n• 📄 CV upload & analysis\n\nJust describe what you love!",
    ar: "هذا ما يمكنني فعله 🚀\n\n• 🔍 إيجاد المهن المناسبة لاهتماماتك\n• 💰 بيانات رواتب حقيقية بالدرهم/الريال/الروبية\n• 🎯 تحليل الفجوة في المهارات\n• 🌍 التوافق مع رؤية 2030/2035\n• 🗺️ خارطة طريق خطوة بخطوة\n• 🎤 إدخال صوتي\n• 📄 تحليل السيرة الذاتية",
    ur: "میں یہ کر سکتا ہوں 🚀\n\n• 🔍 دلچسپیوں سے میل کھاتے کیریئرز\n• 💰 AED/SAR/PKR میں تنخواہ\n• 🎯 مہارت کے فرق کا تجزیہ\n• 🎤 آواز سے ان پٹ\n• 📄 CV تجزیہ",
  },
  whoAreYou: {
    en: "I'm Career Journey AI 🤖 — your intelligent career guidance assistant!\n\nPowered by ML + O*NET (1,000+ careers) + Vision 2030/2035.\n\nI speak Arabic 🇸🇦, Urdu 🇵🇰 & English! I also support voice input and CV analysis.",
    ar: "أنا Career Journey AI 🤖 — مساعدك الذكي في التوجيه المهني!\n\nمدعوم بـ ML + O*NET (أكثر من 1000 مهنة) + رؤية 2030/2035.",
    ur: "میں Career Journey AI 🤖 ہوں!\n\nML + O*NET (1,000+ کیریئرز) + Vision 2030/2035 سے چلتا ہوں۔",
  },
  langSwitch: {
    ar: "تمام! سأتحدث معك بالعربية من الآن. 🌟\n\nأخبرني ما هي اهتماماتك؟",
    ur: "ٹھیک ہے! اب میں آپ سے اردو میں بات کروں گا۔ 🌟\n\nآپ کی دلچسپیاں کیا ہیں؟",
    en: "Got it! Switching to English. 🌟\n\nTell me your interests!",
  },
  speaksArabic: {
    en: "Yes! I speak Arabic fluently 🌟\n\nJust say 'use arabic' and I'll switch all responses to Arabic!",
    ar: "نعم! أتكلم العربية بطلاقة 🌟\n\nقل 'استخدم العربية' وسأتحول للعربية كاملاً!",
    ur: "جی ہاں! میں عربی بول سکتا ہوں 🌟",
  },
  speaksUrdu: {
    en: "Yes! I speak Urdu fluently 🌟\n\nJust say 'use urdu' and I'll switch all responses to Urdu!",
    ur: "جی ہاں! میں اردو میں بات کر سکتا ہوں 🌟\n\nبس 'اردو استعمال کریں' کہیں!",
    ar: "نعم! أتكلم الأردية 🌟",
  },
};

function getReply(key: string, lang: "ar" | "ur" | "en"): string {
  return LANG_REPLIES[key]?.[lang] || LANG_REPLIES[key]?.["en"] || "";
}

function getSmallTalkReply(
  text: string,
  convState: ConvState,
  activeLang: "ar" | "ur" | "en"
): { reply: string | null; newState: ConvState; langSwitch?: "ar" | "ur" | "en" } {
  const lower = text.toLowerCase().trim();

  if (/use arabic|switch to arabic|استخدم العربية|تكلم عربي|بالعربي/.test(lower))
    return { reply: getReply("langSwitch", "ar"), newState: convState, langSwitch: "ar" };
  if (/use urdu|switch to urdu|اردو میں|اردو استعمال|اردو بولو/.test(lower))
    return { reply: getReply("langSwitch", "ur"), newState: convState, langSwitch: "ur" };
  if (/use english|switch to english|speak english|english please/.test(lower))
    return { reply: getReply("langSwitch", "en"), newState: convState, langSwitch: "en" };

  if (/do you (know|speak|understand) arabic|can you (speak|use|write) arabic/.test(lower))
    return { reply: getReply("speaksArabic", activeLang), newState: convState };
  if (/do you (know|speak|understand) urdu|can you (speak|use|write) urdu/.test(lower))
    return { reply: getReply("speaksUrdu", activeLang), newState: convState };

  if (
    /^(hi|hello|hey|howdy|yo|مرحبا|هاي|السلام عليكم|اهلا|هلا|ہیلو|آداب|سلام)[\s!.]*$/.test(lower) ||
    /^(مرحب|أهلا|هلا|سلام عليكم)/.test(text)
  )
    return { reply: getReply("greeting", activeLang), newState: "asked_how_are_you" };

  if (convState === "asked_how_are_you") {
    if (/good|great|fine|well|amazing|okay|alright|مزبوط|تمام|كويس|ممتاز|بخير|ٹھیک|اچھا/.test(lower))
      return { reply: getReply("good", activeLang), newState: "idle" };
    if (/bad|sad|tired|not good|awful|stressed|مو زين|تعبان|برا|تھکا/.test(lower))
      return { reply: getReply("bad", activeLang), newState: "idle" };
    return { reply: null, newState: "idle" };
  }

  if (/how are you|كيفك|كيف حالك|عامل ايه|آپ کیسے ہیں|کیسے ہو/.test(lower))
    return { reply: getReply("howAreYou", activeLang), newState: "asked_how_are_you" };
  if (/thank|thanks|شكرا|مشكور|ممنون|شکریہ/.test(lower))
    return { reply: getReply("thanks", activeLang), newState: convState };
  if (/bye|goodbye|مع السلامة|باي|خدا حافظ|الوداع/.test(lower))
    return { reply: getReply("bye", activeLang), newState: "idle" };
  if (/stupid|idiot|dumb|useless|hate|worst|غبي|احمق|بیوقوف|فضول/.test(lower))
    return { reply: getReply("badWords", activeLang), newState: convState };
  if (/i don't know|idk|not sure|confused|لا أعرف|مش عارف|پتہ نہیں|معلوم نہیں/.test(lower))
    return { reply: getReply("confused", activeLang), newState: convState };
  if (/what can you do|help me|how does this work|كيف تشتغل|آپ کیا کر سکتے/.test(lower))
    return { reply: getReply("whatCanYouDo", activeLang), newState: convState };
  if (/who are you|what are you|are you ai|من أنت|آپ کون ہیں/.test(lower))
    return { reply: getReply("whoAreYou", activeLang), newState: convState };

  const jokeWords = /^(lol|haha|hehe|kidding|joking|just kidding|test|testing|asdf|qwerty|blah|nothing|idk|whatever|random|bored|hi there|hey there|sup|wassup|yo+|ok|okay|k|yes|no|maybe|sure|cool|nice|great|wow|omg|wtf|hmm|uh|um|err)[\s!?.]*$/;
  if (jokeWords.test(lower) || lower.length < 3)
    return {
      reply: activeLang === "ar"
        ? `يبدو أن هذا ليس وصفاً لاهتمام مهني 😄\n\nجرب مثلاً: 'أحب البرمجة' أو 'أستمتع بمساعدة الناس'`
        : activeLang === "ur"
        ? `یہ کیریئر کی دلچسپی نہیں لگتی 😄\n\nمثال کے طور پر: 'مجھے پروگرامنگ پسند ہے'`
        : `That doesn't sound like a career interest 😄\n\nTry something like: 'I love coding' or 'I enjoy helping people'`,
      newState: convState
    };
  if (/^\d+$/.test(lower))
    return {
      reply: activeLang === "ar"
        ? "هذا رقم فقط! 😄 جرب وصف اهتماماتك بدلاً من ذلك."
        : activeLang === "ur"
        ? "یہ صرف ایک نمبر ہے! 😄 اس کی بجائے اپنی دلچسپیاں بیان کریں۔"
        : "That looks like a number! 😄 Try describing your interests instead!",
      newState: convState,
    };

  return { reply: null, newState: convState };
}

// ─── Animated Background ──────────────────────────────────────────────────────
function AnimatedBackground({ dark }: { dark: boolean }) {
  return (
    <div className="fixed inset-0 pointer-events-none overflow-hidden z-0">
      <style>{`
        @keyframes drift1{0%{transform:translateX(0) translateY(0) rotate(0deg)}25%{transform:translateX(40px) translateY(-30px) rotate(90deg)}50%{transform:translateX(80px) translateY(20px) rotate(180deg)}75%{transform:translateX(20px) translateY(50px) rotate(270deg)}100%{transform:translateX(0) translateY(0) rotate(360deg)}}
        @keyframes drift2{0%{transform:translateX(0) translateY(0)}33%{transform:translateX(-50px) translateY(40px)}66%{transform:translateX(30px) translateY(-50px)}100%{transform:translateX(0) translateY(0)}}
        @keyframes drift3{0%{transform:translateX(0) translateY(0) scale(1)}50%{transform:translateX(-30px) translateY(-40px) scale(1.1)}100%{transform:translateX(0) translateY(0) scale(1)}}
        @keyframes lineMove{0%{transform:translateY(-100%);opacity:0}10%{opacity:1}90%{opacity:1}100%{transform:translateY(100vh);opacity:0}}
        @keyframes twinkle{0%,100%{opacity:0.1;transform:scale(1)}50%{opacity:0.6;transform:scale(1.4)}}
        .d1{animation:drift1 20s ease-in-out infinite}.d2{animation:drift2 25s ease-in-out infinite}.d3{animation:drift3 18s ease-in-out infinite}.d4{animation:drift1 30s ease-in-out infinite reverse}
        .lm1{animation:lineMove 7s linear infinite}.lm2{animation:lineMove 10s linear infinite 2s}.lm3{animation:lineMove 8s linear infinite 4s}.lm4{animation:lineMove 12s linear infinite 1s}
        .twk{animation:twinkle 3s ease-in-out infinite}
      `}</style>
      <div className={`absolute inset-0 ${dark ? "bg-gradient-to-br from-[#050e05] via-[#071407] to-[#050e05]" : "bg-gradient-to-br from-[#e8eaf6] via-[#f3f4ff] to-[#e8eaf6]"}`} />
      <div className={`d1 absolute top-[-10%] left-[-5%] w-[45vw] h-[45vw] rounded-[40%_60%_55%_45%] opacity-[0.10] blur-[60px] ${dark ? "bg-emerald-800" : "bg-emerald-200"}`} />
      <div className={`d2 absolute bottom-[-10%] right-[-5%] w-[50vw] h-[50vw] rounded-[55%_45%_40%_60%] opacity-[0.08] blur-[70px] ${dark ? "bg-green-900" : "bg-green-200"}`} />
      <div className={`d3 absolute top-[30%] right-[10%] w-[30vw] h-[30vw] rounded-[50%] opacity-[0.07] blur-[50px] ${dark ? "bg-teal-800" : "bg-teal-200"}`} />
      <div className={`d4 absolute bottom-[20%] left-[5%] w-[25vw] h-[25vw] rounded-[60%_40%_50%_50%] opacity-[0.06] blur-[45px] ${dark ? "bg-emerald-900" : "bg-indigo-200"}`} />
      {[
        { cls: "lm1", l: "15%", c: dark ? "rgba(74,222,128,0.25)" : "rgba(99,102,241,0.12)" },
        { cls: "lm2", l: "40%", c: dark ? "rgba(34,197,94,0.2)" : "rgba(139,92,246,0.1)" },
        { cls: "lm3", l: "65%", c: dark ? "rgba(16,185,129,0.2)" : "rgba(6,182,212,0.08)" },
        { cls: "lm4", l: "85%", c: dark ? "rgba(52,211,153,0.15)" : "rgba(167,139,250,0.1)" },
      ].map((l, i) => (
        <div key={i} className={l.cls} style={{ position: "absolute", left: l.l, top: 0, width: 1, height: 100, background: `linear-gradient(to bottom,transparent,${l.c},transparent)` }} />
      ))}
      {[
        { t: "8%", l: "20%", d: "0s" }, { t: "15%", l: "75%", d: "0.8s" },
        { t: "35%", l: "10%", d: "1.5s" }, { t: "55%", l: "88%", d: "0.3s" },
        { t: "70%", l: "50%", d: "2.1s" }, { t: "85%", l: "30%", d: "1.1s" },
        { t: "25%", l: "55%", d: "1.7s" }, { t: "90%", l: "70%", d: "0.5s" },
      ].map((s, i) => (
        <div key={i} className="twk" style={{ position: "absolute", top: s.t, left: s.l, width: 3, height: 3, borderRadius: "50%", backgroundColor: dark ? "#a5b4fc" : "#6366f1", boxShadow: `0 0 6px ${dark ? "#a5b4fc" : "#6366f1"}`, animationDelay: s.d }} />
      ))}
      <div className="absolute inset-0 opacity-[0.025]" style={{ backgroundImage: `linear-gradient(${dark ? "#fff" : "#000"} 1px,transparent 1px),linear-gradient(90deg,${dark ? "#fff" : "#000"} 1px,transparent 1px)`, backgroundSize: "60px 60px" }} />
    </div>
  );
}

// ─── Career Components ────────────────────────────────────────────────────────
function Section({ title, children, dark }: { title: string; children: React.ReactNode; dark: boolean }) {
  return (
    <div className="mb-5">
      <div className={`text-xs font-bold uppercase tracking-widest mb-1.5 ${dark ? "text-indigo-400" : "text-indigo-600"}`}>{title}</div>
      <div className={`text-sm leading-relaxed ${dark ? "text-gray-200" : "text-gray-700"}`}>{children}</div>
    </div>
  );
}

function SkillsGap({ have, missing, dark }: { have: string[]; missing: string[]; dark: boolean }) {
  if (!have.length && !missing.length) return null;
  const pct = Math.round(have.length / Math.max(have.length + missing.length, 1) * 100);
  return (
    <div className="mb-5">
      <div className={`text-xs font-bold uppercase tracking-widest mb-2 ${dark ? "text-indigo-400" : "text-indigo-600"}`}>🎯 Skills Gap Analysis</div>
      {have.length > 0 && (
        <div className="mb-2">
          <div className={`text-xs mb-1.5 ${dark ? "text-gray-400" : "text-gray-500"}`}>✅ You already have:</div>
          <div className="flex flex-wrap gap-1.5">
            {have.map((s, i) => <span key={i} className={`text-xs px-2.5 py-1 rounded-full ${dark ? "bg-green-900/40 text-green-400 border border-green-800" : "bg-green-50 text-green-700 border border-green-200"}`}>{s}</span>)}
          </div>
        </div>
      )}
      {missing.length > 0 && (
        <div className="mb-2">
          <div className={`text-xs mb-1.5 ${dark ? "text-gray-400" : "text-gray-500"}`}>📚 Skills to learn:</div>
          <div className="flex flex-wrap gap-1.5">
            {missing.map((s, i) => <span key={i} className={`text-xs px-2.5 py-1 rounded-full ${dark ? "bg-red-900/30 text-red-400 border border-red-900" : "bg-red-50 text-red-600 border border-red-200"}`}>{s}</span>)}
          </div>
        </div>
      )}
      {have.length > 0 && (
        <div>
          <div className={`text-xs mb-1 ${dark ? "text-gray-400" : "text-gray-500"}`}>Match: {pct}%</div>
          <div className={`h-1.5 rounded-full ${dark ? "bg-gray-800" : "bg-gray-200"}`}>
            <div className="h-full rounded-full bg-indigo-500 transition-all" style={{ width: `${pct}%` }} />
          </div>
        </div>
      )}
    </div>
  );
}

function VisionBadge({ vision, dark }: { vision: NonNullable<CareerResult["vision_alignment"]>; dark: boolean }) {
  return (
    <div className={`rounded-xl border p-3 mb-4 ${dark ? "bg-green-950/60 border-green-900/60" : "bg-green-50 border-green-200"}`}>
      <div className="flex items-center gap-2 mb-1">
        <span className="text-lg">{vision.flag}</span>
        <span className={`text-xs font-bold ${dark ? "text-green-400" : "text-green-700"}`}>{vision.vision_label} Aligned</span>
        <span className={`ml-auto text-xs px-2 py-0.5 rounded-full ${dark ? "bg-green-900/40 text-green-400" : "bg-green-100 text-green-700"}`}>{vision.demand}</span>
      </div>
      <div className={`text-xs ${dark ? "text-gray-400" : "text-gray-500"}`}>
        Sector: <span className={`font-semibold ${dark ? "text-white" : "text-black"}`}>{vision.sector}</span> · Growth: <span className="text-green-500 font-semibold">{vision.growth}</span>
      </div>
    </div>
  );
}

function CareerPanel({ data, dark }: { data: CareerResult; dark: boolean }) {
  const [showRoadmap, setShowRoadmap] = useState(false);
  const isTech = data.source === "tech_dataset";
  const pros = [
    data.future_demand === "Very High" ? "Extremely high job market demand — jobs are easy to find" :
      data.future_demand === "High" ? "Strong job market demand with many openings" : "Stable job market with consistent opportunities",
    data.estimated_salary && data.estimated_salary > 100000 ? "Above-average salary with strong earning potential" :
      data.estimated_salary && data.estimated_salary > 60000 ? "Competitive salary for most regions" : "Salary varies — top performers can earn significantly",
    "Clear progression path with defined milestones",
    "Growing demand across UAE, KSA & Pakistan markets",
  ];
  const cons = [
    data.education_required?.toLowerCase().includes("doctoral") ? "Requires many years of education (PhD or doctoral level)" : "Competitive field — continuous learning is essential",
    "Rapid change means you must keep your skills updated",
    isTech ? "High competition from global talent, especially in remote roles" : "Career growth may require additional certifications",
  ];
  return (
    <div className={`rounded-2xl border p-5 ${dark ? "bg-[#13131f]/70 border-gray-700/60" : "bg-white/70 border-gray-200"} backdrop-blur-md`}>
      {data.vision_alignment && <VisionBadge vision={data.vision_alignment} dark={dark} />}
      {data.description && <Section title="📋 About This Career" dark={dark}>{data.description}</Section>}
      <Section title="💰 Salary & Compensation" dark={dark}>
        {data.estimated_salary
          ? <><strong>{data.salary_range || `${Math.round(data.estimated_salary * 0.8).toLocaleString()}–${Math.round(data.estimated_salary * 1.2).toLocaleString()}`} {data.currency}/yr</strong>, based on {data.data_points > 0 ? `${data.data_points.toLocaleString()} real salary records` : "market data"}. At <strong>{data.experience_level || "Mid-level"}</strong> level, expect around <strong>{data.salary_display || `${data.estimated_salary.toLocaleString()} ${data.currency}/yr`}</strong>.</>
          : <>Salary varies by specialization. Research local benchmarks in <strong>{data.region}</strong> for <strong>{data.experience_level || "Mid-level"}</strong> level professionals.</>}
      </Section>
      {data.education_required && (
        <Section title="🎓 Education Requirements" dark={dark}>
          Most professionals hold a <strong>{String(data.education_required).replace(/^\d+\.?\d*\s*/, '') || data.education_required}</strong>. Entry-level may accept related certifications, but advancing typically requires formal qualifications.
        </Section>
      )}
      <Section title="📈 Market Demand & Future Outlook" dark={dark}>
        Demand is currently <strong>{data.future_demand}</strong>.{" "}
        {data.future_demand === "Very High" && "This field is growing rapidly — excellent job security in UAE, KSA & Pakistan."}
        {data.future_demand === "High" && "A stable and growing field with many opportunities across the region."}
        {data.future_demand === "Medium-High" && "Growing steadily — opportunities exist but competition is increasing."}
        {data.future_demand === "Medium" && "Consistent demand. Specialization helps stand out in the local market."}
      </Section>
      <SkillsGap have={data.skills_you_have || []} missing={data.skills_to_learn || []} dark={dark} />
      {(data.required_skills?.length ?? 0) > 0 && (
        <Section title="🛠️ Key Skills Needed" dark={dark}>
          Core skills: <strong>{data.required_skills.join(", ")}</strong>.
          {isTech && " Ranked by frequency across thousands of job postings in the region."}
        </Section>
      )}
      {(data.certifications?.length ?? 0) > 0 && (
        <Section title="📜 Recommended Certifications" dark={dark}>
          Most valued: <strong>{data.certifications.join(", ")}</strong>. These significantly boost salary and employability in {data.region}.
        </Section>
      )}
      <Section title="✅ Advantages" dark={dark}>
        <ul className="flex flex-col gap-1.5 mt-1">
          {pros.map((p, i) => <li key={i} className="flex items-start gap-2"><span className={`mt-0.5 flex-shrink-0 ${dark ? "text-green-400" : "text-green-600"}`}>▸</span><span>{p}</span></li>)}
        </ul>
      </Section>
      <Section title="⚠️ Challenges" dark={dark}>
        <ul className="flex flex-col gap-1.5 mt-1">
          {cons.map((c, i) => <li key={i} className="flex items-start gap-2"><span className="text-red-400 mt-0.5 flex-shrink-0">▸</span><span>{c}</span></li>)}
        </ul>
      </Section>
      {(data.roadmap?.length ?? 0) > 0 && (
        <div>
          <button onClick={() => setShowRoadmap(v => !v)}
            className={`flex items-center gap-2 text-xs font-bold uppercase tracking-widest mb-2 ${dark ? "text-indigo-400 hover:text-indigo-300" : "text-indigo-600 hover:text-indigo-500"} transition-colors`}>
            <span>🗺️ Career Roadmap</span>
            {showRoadmap ? <ChevronUp size={13} /> : <ChevronDown size={13} />}
            <span className={`normal-case font-normal ${dark ? "text-gray-500" : "text-gray-400"}`}>({data.roadmap.length} steps)</span>
          </button>
          {showRoadmap && (
            <ol className="flex flex-col gap-2">
              {data.roadmap.map((step, i) => (
                <li key={i} className="flex items-start gap-3">
                  <span className="w-5 h-5 rounded-full bg-indigo-600 text-white flex items-center justify-center text-xs font-bold flex-shrink-0 mt-0.5">{i + 1}</span>
                  <span className={`text-sm ${dark ? "text-gray-300" : "text-gray-700"}`}>{step}</span>
                </li>
              ))}
            </ol>
          )}
        </div>
      )}
    </div>
  );
}

function ComparisonTable({ recommendations, dark }: { recommendations: CareerResult[]; dark: boolean }) {
  return (
    <div className={`rounded-2xl border overflow-hidden backdrop-blur-md ${dark ? "bg-[#13131f]/70 border-gray-700/60" : "bg-white/70 border-gray-200"}`}>
      <div className={`px-5 py-3 font-bold text-sm border-b ${dark ? "bg-[#1a1a2e]/80 border-gray-700 text-white" : "bg-gray-50/80 border-gray-200 text-black"}`}>⚖️ Side-by-Side Comparison</div>
      <div className="overflow-x-auto">
        <table className="w-full text-xs">
          <thead>
            <tr className={dark ? "bg-[#12122a]/60" : "bg-gray-50/60"}>
              {["Career", "Match", "Salary", "Demand", "Education", "Top Skill", "Vision"].map(h => (
                <th key={h} className={`text-left px-4 py-2.5 font-semibold ${dark ? "text-gray-400" : "text-gray-500"}`}>{h}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {recommendations.map((rec, i) => (
              <tr key={i} className={`border-t ${dark ? "border-gray-800 hover:bg-[#1e1e3a]/50" : "border-gray-100 hover:bg-gray-50"} transition-colors`}>
                <td className={`px-4 py-2.5 font-semibold ${dark ? "text-white" : "text-black"}`}>{["🥇","🥈","🥉","⭐","⭐","⭐"][i]} {rec.career_title}</td>
                <td className="px-4 py-2.5"><span className={`font-bold ${rec.confidence > 15 ? "text-green-400" : rec.confidence > 10 ? "text-yellow-400" : "text-gray-400"}`}>{rec.confidence}%</span></td>
                <td className={`px-4 py-2.5 ${dark ? "text-gray-300" : "text-gray-600"}`}>{rec.salary_display || "Varies"}</td>
                <td className="px-4 py-2.5">
                  <span className={`px-2 py-0.5 rounded-full text-xs font-medium ${rec.future_demand === "Very High" ? (dark ? "bg-green-900/40 text-green-400" : "bg-green-100 text-green-700") : rec.future_demand === "High" ? (dark ? "bg-blue-900/40 text-blue-400" : "bg-blue-100 text-blue-700") : (dark ? "bg-yellow-900/40 text-yellow-400" : "bg-yellow-100 text-yellow-700")}`}>{rec.future_demand}</span>
                </td>
                <td className={`px-4 py-2.5 ${dark ? "text-gray-300" : "text-gray-600"} max-w-[100px] truncate`}>{rec.education_required?.toString().replace(/^\d+\.?\d*\s*/, "") || "Varies"}</td>
                <td className={`px-4 py-2.5 ${dark ? "text-gray-300" : "text-gray-600"}`}>{rec.required_skills?.[0] || "—"}</td>
                <td className="px-4 py-2.5">{rec.vision_alignment ? `${rec.vision_alignment.flag} ${rec.vision_alignment.sector}` : "—"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function RecommendationsCard({ recommendations, dark }: { recommendations: CareerResult[]; dark: boolean }) {
  const [selected, setSelected] = useState(0);
  const [showComparison, setShowComparison] = useState(false);
  const medals = ["🥇", "🥈", "🥉", "⭐", "⭐", "⭐"];
  return (
    <div className="flex flex-col gap-4 w-full">
      <div className={`text-sm font-medium ${dark ? "text-gray-300" : "text-gray-600"}`}>
        Found <span className={`font-bold ${dark ? "text-white" : "text-black"}`}>{recommendations.length}</span> matching career{recommendations.length > 1 ? "s" : ""} — pick one to see full details:
      </div>
      <div className="flex gap-2 overflow-x-auto pb-1" style={{ scrollbarWidth: "none" }}>
        {recommendations.map((rec, i) => (
          <button key={i} onClick={() => setSelected(i)}
            className={`flex flex-col items-start px-4 py-2.5 rounded-xl border transition-all whitespace-nowrap flex-shrink-0 min-w-[130px] backdrop-blur-sm
              ${selected === i
                ? dark ? "bg-indigo-600/80 border-indigo-500 text-white shadow-lg shadow-indigo-900/30" : "bg-indigo-600 border-indigo-500 text-white shadow-lg"
                : dark ? "bg-[#1a1a2e]/60 border-gray-700 text-gray-400 hover:text-white hover:border-gray-500" : "bg-white/60 border-gray-200 text-gray-500 hover:text-black hover:bg-gray-50"}`}>
            <div className="flex items-center gap-1.5 mb-0.5">
              <span className="text-base">{medals[i]}</span>
              <span className={`text-xs font-bold px-1.5 py-0.5 rounded-full ${selected === i ? "bg-white/20 text-white" : dark ? "bg-indigo-900/40 text-indigo-400" : "bg-indigo-100 text-indigo-600"}`}>{rec.confidence}%</span>
            </div>
            <div className="text-xs font-semibold leading-tight max-w-[160px] text-left" style={{ whiteSpace: "normal" }}>{rec.career_title}</div>
            {rec.vision_alignment && <div className="text-xs mt-0.5">{rec.vision_alignment.flag}</div>}
          </button>
        ))}
      </div>
      <div className={`border-t ${dark ? "border-gray-700/60" : "border-gray-200"}`} />
      <div>
        <div className={`text-xl font-bold ${dark ? "text-white" : "text-black"}`}>{medals[selected]} {recommendations[selected].career_title}</div>
        {recommendations[selected].tech_field !== "General Career" && (
          <div className={`text-xs mt-0.5 ${dark ? "text-indigo-400" : "text-indigo-600"}`}>{recommendations[selected].tech_field}</div>
        )}
      </div>
      <CareerPanel data={recommendations[selected]} dark={dark} />
      {recommendations.length > 1 && (
        <button onClick={() => setShowComparison(v => !v)}
          className={`flex items-center justify-center gap-2 py-2.5 rounded-xl border text-sm font-medium transition-all backdrop-blur-sm
            ${dark ? "border-gray-700 text-gray-400 hover:text-white hover:border-gray-500 bg-[#1a1a2e]/40" : "border-gray-300 text-gray-500 hover:text-black bg-white/40"}`}>
          {showComparison ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
          {showComparison ? "Hide" : "Show"} side-by-side comparison of all {recommendations.length} careers
        </button>
      )}
      {showComparison && <ComparisonTable recommendations={recommendations} dark={dark} />}
    </div>
  );
}

// ─── Admin Dashboard ──────────────────────────────────────────────────────────
function AdminDashboard({ dark }: { dark: boolean }) {
  const mockStats = {
    total_searches: 1284, total_occupations: 1016, tech_fields: 14, salary_records: 50000,
    popular_careers: [["Software Developer", 342], ["Data Scientist", 289], ["Cybersecurity Analyst", 201], ["DevOps Engineer", 178], ["Product Manager", 134]],
    popular_regions: [["UAE", 456], ["KSA", 312], ["Pakistan", 189]],
    recent_searches: [
      { timestamp: "2024-01-15T10:30:00", query: "I love coding and AI", region: "UAE", results: 4 },
      { timestamp: "2024-01-15T10:28:00", query: "healthcare and helping people", region: "KSA", results: 6 },
      { timestamp: "2024-01-15T10:25:00", query: "أحب التصميم والإبداع", region: "KSA", results: 5 },
      { timestamp: "2024-01-15T10:20:00", query: "مجھے ٹیکنالوجی پسند ہے", region: "Pakistan", results: 4 },
    ]
  };
  const [stats, setStats] = useState<any>(mockStats);

  useEffect(() => {
    fetch("https://amrqahtan-career-ai-backend.hf.space/admin/stats")
      .then(res => res.json())
      .then(data => setStats({ ...mockStats, ...data }))
      .catch(() => setStats(mockStats));
  }, []);
  
  const cards = [
    { icon: <BarChart2 size={20} />, label: "Total Searches", value: stats.total_searches.toLocaleString(), color: "text-indigo-400" },
    { icon: <Briefcase size={20} />, label: "Career Occupations", value: stats.total_occupations.toLocaleString(), color: "text-blue-400" },
    { icon: <Users size={20} />, label: "Salary Records", value: stats.salary_records.toLocaleString(), color: "text-purple-400" },
    { icon: <Globe size={20} />, label: "Regions", value: "UAE · KSA · Pakistan", color: "text-green-400" },
  ];
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className={`text-2xl font-bold mb-1 ${dark ? "text-white" : "text-black"}`}>⚙️ Admin Dashboard</div>
      <div className={`text-sm mb-6 ${dark ? "text-gray-400" : "text-gray-500"}`}>System overview and real-time analytics</div>
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 mb-6">
        {cards.map((c, i) => (
          <div key={i} className={`rounded-2xl border p-4 backdrop-blur-md ${dark ? "bg-[#13131f]/80 border-gray-700/60" : "bg-white/80 border-gray-200"}`}>
            <div className={`${c.color} mb-2`}>{c.icon}</div>
            <div className={`text-2xl font-bold ${dark ? "text-white" : "text-black"}`}>{c.value}</div>
            <div className={`text-xs ${dark ? "text-gray-400" : "text-gray-500"}`}>{c.label}</div>
          </div>
        ))}
      </div>
      <div className="grid md:grid-cols-2 gap-4 mb-4">
        <div className={`rounded-2xl border p-4 ${dark ? "bg-[#13131f]/80 border-gray-700/60" : "bg-white/80 border-gray-200"}`}>
          <div className={`text-sm font-bold mb-3 ${dark ? "text-indigo-400" : "text-indigo-600"}`}>🔥 Top Career Searches</div>
          {stats.popular_careers.map(([career, count], i) => (
            <div key={i} className={`flex items-center gap-3 py-1.5 ${i < 4 ? "border-b" : ""} ${dark ? "border-gray-800" : "border-gray-100"}`}>
              <span className={`text-xs w-5 ${dark ? "text-gray-500" : "text-gray-400"}`}>{i + 1}.</span>
              <span className={`text-sm flex-1 ${dark ? "text-white" : "text-black"}`}>{career}</span>
              <span className={`text-xs font-bold ${dark ? "text-indigo-400" : "text-indigo-600"}`}>{count}</span>
              <div className={`h-1.5 rounded-full ${dark ? "bg-gray-800" : "bg-gray-200"}`} style={{ width: 80 }}>
                <div className="h-full rounded-full bg-indigo-500" style={{ width: `${(Number(count) / 342) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
        <div className={`rounded-2xl border p-4 ${dark ? "bg-[#13131f]/80 border-gray-700/60" : "bg-white/80 border-gray-200"}`}>
          <div className={`text-sm font-bold mb-3 ${dark ? "text-indigo-400" : "text-indigo-600"}`}>🌍 Users by Region</div>
          {stats.popular_regions.map(([region, count], i) => (
            <div key={i} className={`flex items-center gap-3 py-1.5 ${i < 2 ? "border-b" : ""} ${dark ? "border-gray-800" : "border-gray-100"}`}>
              <span className="text-lg">{region === "UAE" ? "🇦🇪" : region === "KSA" ? "🇸🇦" : "🇵🇰"}</span>
              <span className={`text-sm flex-1 ${dark ? "text-white" : "text-black"}`}>{region}</span>
              <span className={`text-xs font-bold ${dark ? "text-indigo-400" : "text-indigo-600"}`}>{count}</span>
              <div className={`h-1.5 rounded-full ${dark ? "bg-gray-800" : "bg-gray-200"}`} style={{ width: 80 }}>
                <div className="h-full rounded-full bg-indigo-500" style={{ width: `${(Number(count) / 456) * 100}%` }} />
              </div>
            </div>
          ))}
        </div>
      </div>
      <div className={`rounded-2xl border p-4 ${dark ? "bg-[#13131f]/80 border-gray-700/60" : "bg-white/80 border-gray-200"}`}>
        <div className={`text-sm font-bold mb-3 ${dark ? "text-indigo-400" : "text-indigo-600"}`}>🕐 Recent Searches (Arabic/Urdu/English)</div>
        <table className="w-full text-xs">
          <thead><tr>{["Time", "Query", "Region", "Lang", "Results"].map(h => <th key={h} className={`text-left px-3 py-2 ${dark ? "text-gray-400" : "text-gray-500"}`}>{h}</th>)}</tr></thead>
          <tbody>{stats.recent_searches.map((s, i) => {
            const lang = detectLanguage(s.query);
            return <tr key={i} className={`border-t ${dark ? "border-gray-800" : "border-gray-100"}`}>
              <td className={`px-3 py-2 ${dark ? "text-gray-400" : "text-gray-500"}`}>{new Date(s.timestamp).toLocaleTimeString()}</td>
              <td className={`px-3 py-2 ${dark ? "text-white" : "text-black"}`} dir={lang !== "en" ? "rtl" : "ltr"}>{s.query}</td>
              <td className="px-3 py-2">{s.region === "UAE" ? "🇦🇪" : s.region === "KSA" ? "🇸🇦" : "🇵🇰"} {s.region}</td>
              <td className={`px-3 py-2 font-bold ${lang === "ar" ? "text-yellow-400" : lang === "ur" ? "text-green-400" : "text-blue-400"}`}>{lang.toUpperCase()}</td>
              <td className={`px-3 py-2 ${dark ? "text-gray-400" : "text-gray-500"}`}>{s.results}</td>
            </tr>;
          })}</tbody>
        </table>
      </div>
    </div>
  );
}

// ─── Client Dashboard ─────────────────────────────────────────────────────────
function ClientDashboard({ dark }: { dark: boolean }) {
  const [region, setRegion] = useState("KSA");
  const VISIONS: Record<string, any> = {
    KSA: {
      label: "Saudi Vision 2030", flag: "🇸🇦", currency: "SAR", sectors: [
        { name: "Technology & Digital", demand: "Very High", growth: "+200% by 2030", jobs: ["Software Developer", "Data Scientist", "Cloud Engineer", "AI Specialist"] },
        { name: "Tourism & Hospitality", demand: "Very High", growth: "+150% by 2030", jobs: ["Hotel Manager", "Tourism Specialist", "Event Planner", "Travel Guide"] },
        { name: "Healthcare", demand: "Very High", growth: "+80% by 2030", jobs: ["Physician", "Nurse", "Pharmacist", "Medical Researcher"] },
        { name: "Entertainment & Sports", demand: "High", growth: "+120% by 2030", jobs: ["Game Designer", "Media Producer", "Sports Coach", "Content Creator"] },
        { name: "Renewable Energy", demand: "High", growth: "+90% by 2030", jobs: ["Solar Engineer", "Environmental Scientist", "Energy Analyst", "Green Architect"] },
        { name: "Financial Services", demand: "High", growth: "+60% by 2030", jobs: ["Financial Analyst", "FinTech Developer", "Investment Banker", "Risk Manager"] },
      ]
    },
    UAE: {
      label: "UAE Vision 2030", flag: "🇦🇪", currency: "AED", sectors: [
        { name: "AI & Smart Cities", demand: "Very High", growth: "+250% by 2030", jobs: ["AI Engineer", "Smart City Planner", "IoT Developer", "Data Scientist"] },
        { name: "FinTech & Banking", demand: "Very High", growth: "+180% by 2030", jobs: ["FinTech Developer", "Blockchain Engineer", "Digital Banker", "Crypto Analyst"] },
        { name: "Logistics & Trade", demand: "High", growth: "+70% by 2030", jobs: ["Supply Chain Manager", "Logistics Analyst", "Trade Specialist", "Port Manager"] },
        { name: "Healthcare Innovation", demand: "Very High", growth: "+100% by 2030", jobs: ["Biomedical Engineer", "Health Informatics", "Medical AI Specialist", "Telemedicine Doctor"] },
        { name: "Space & Aviation", demand: "High", growth: "+85% by 2030", jobs: ["Aerospace Engineer", "Pilot", "Space Scientist", "Aviation Manager"] },
        { name: "Creative Economy", demand: "Medium-High", growth: "+60% by 2030", jobs: ["UI/UX Designer", "Content Creator", "Digital Marketer", "Film Director"] },
      ]
    },
    Pakistan: {
      label: "Pakistan Vision 2035", flag: "🇵🇰", currency: "PKR", sectors: [
        { name: "IT & Freelancing", demand: "Very High", growth: "+300% by 2035", jobs: ["Web Developer", "Mobile Developer", "Freelance Designer", "Digital Marketer"] },
        { name: "Healthcare", demand: "Very High", growth: "+90% by 2035", jobs: ["Doctor", "Nurse", "Pharmacist", "Telemedicine Specialist"] },
        { name: "Education Technology", demand: "High", growth: "+120% by 2035", jobs: ["E-Learning Developer", "Education Consultant", "Online Instructor", "EdTech Designer"] },
        { name: "Agriculture Tech", demand: "High", growth: "+80% by 2035", jobs: ["AgriTech Specialist", "Food Scientist", "Agricultural Engineer", "Smart Farming Analyst"] },
        { name: "Renewable Energy", demand: "High", growth: "+100% by 2035", jobs: ["Solar Engineer", "Energy Consultant", "Power Systems Engineer", "Green Building Specialist"] },
        { name: "Textile & Manufacturing", demand: "Medium-High", growth: "+50% by 2035", jobs: ["Fashion Designer", "Production Manager", "Quality Engineer", "Textile Technologist"] },
      ]
    },
  };
  const cur = VISIONS[region];
  return (
    <div className="p-6 max-w-5xl mx-auto">
      <div className={`text-2xl font-bold mb-1 ${dark ? "text-white" : "text-black"}`}>🏢 Client / Employer View</div>
      <div className={`text-sm mb-4 ${dark ? "text-gray-400" : "text-gray-500"}`}>Vision 2030/2035 sector insights & top career opportunities</div>
      <div className="flex gap-3 mb-6">
        {REGIONS.map(r => (
          <button key={r.value} onClick={() => setRegion(r.value)}
            className={`px-4 py-2 rounded-xl border text-sm font-medium transition-all
              ${region === r.value
                ? dark ? "bg-indigo-600/80 border-indigo-500 text-white" : "bg-indigo-600 border-indigo-500 text-white"
                : dark ? "bg-[#1a1a2e]/60 border-gray-700 text-gray-400 hover:text-white" : "bg-white/60 border-gray-200 text-gray-500 hover:text-black"}`}>
            {r.label}
          </button>
        ))}
      </div>
      <div className={`rounded-2xl border p-4 mb-6 ${dark ? "bg-green-950/40 border-green-900/60" : "bg-green-50 border-green-200"}`}>
        <div className="flex items-center gap-3">
          <span className="text-3xl">{cur.flag}</span>
          <div>
            <div className={`text-lg font-bold ${dark ? "text-white" : "text-black"}`}>{cur.label}</div>
            <div className={`text-sm ${dark ? "text-gray-400" : "text-gray-500"}`}>Salaries shown in {cur.currency} · High-demand sectors</div>
          </div>
        </div>
      </div>
      <div className="grid md:grid-cols-2 gap-4">
        {cur.sectors.map((sector: any, i: number) => (
          <div key={i} className={`rounded-2xl border p-4 backdrop-blur-md ${dark ? "bg-[#13131f]/80 border-gray-700/60" : "bg-white/80 border-gray-200"}`}>
            <div className="flex items-start justify-between mb-2">
              <div className={`font-bold text-sm ${dark ? "text-white" : "text-black"}`}>{sector.name}</div>
              <span className={`text-xs px-2 py-0.5 rounded-full ${sector.demand === "Very High" ? (dark ? "bg-green-900/40 text-green-400" : "bg-green-100 text-green-700") : sector.demand === "High" ? (dark ? "bg-blue-900/40 text-blue-400" : "bg-blue-100 text-blue-700") : (dark ? "bg-yellow-900/40 text-yellow-400" : "bg-yellow-100 text-yellow-700")}`}>{sector.demand}</span>
            </div>
            <div className="text-xs font-semibold text-green-500 mb-3">{sector.growth}</div>
            <div className={`text-xs font-semibold mb-2 ${dark ? "text-gray-400" : "text-gray-500"}`}>Top Roles:</div>
            <div className="flex flex-wrap gap-1.5">
              {sector.jobs.map((job: string, j: number) => (
                <span key={j} className={`text-xs px-2 py-1 rounded-lg ${dark ? "bg-indigo-900/40 text-indigo-300" : "bg-indigo-100 text-indigo-700"}`}>{job}</span>
              ))}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── Main App ─────────────────────────────────────────────────────────────────
export default function Home() {
  const [input, setInput] = useState("");
  const [messages, setMessages] = useState<Message[]>([]);
  const [dark, setDark] = useState(true);
  const [isLoading, setIsLoading] = useState(false);
  const [convState, setConvState] = useState<ConvState>("idle");
  const [view, setView] = useState<DashboardView>("user");
  const [showPasswordModal, setShowPasswordModal] = useState(false);
  const [passwordInput, setPasswordInput] = useState("");
  const [pendingView, setPendingView] = useState<DashboardView | null>(null);
  const [passwordError, setPasswordError] = useState("");
  const [region, setRegion] = useState("UAE");
  const [activeLang, setActiveLang] = useState<"en" | "ar" | "ur">("en");
  const [isListening, setIsListening] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const recognitionRef = useRef<SpeechRecognition | null>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);

  useEffect(() => { messagesEndRef.current?.scrollIntoView({ behavior: "smooth" }); }, [messages]);

  const selectedRegion = REGIONS.find(r => r.value === region) || REGIONS[0];

  // ── Password Modal Handler ─────────────────────────────────────────────────
  const handlePasswordUnlock = () => {
    const correct = pendingView === "admin" ? "admin123" : "client123";
    if (passwordInput === correct) {
      setView(pendingView!);
      setShowPasswordModal(false);
    } else {
      setPasswordError("Wrong password. Try again.");
    }
  };

  // ── Voice Input ────────────────────────────────────────────────────────────
  const startListening = useCallback(() => {
    const SR =
      (window as any).SpeechRecognition ||
      (window as any).webkitSpeechRecognition;
    if (!SR) { alert("Voice input requires Chrome browser."); return; }
    const rec = new SR();
    rec.lang = activeLang === "ar" ? "ar-SA" : activeLang === "ur" ? "ur-PK" : "en-US";
    rec.interimResults = false;
    rec.onresult = (e: SpeechRecognitionEvent) => {
      setInput(e.results[0][0].transcript);
      setIsListening(false);
    };
    rec.onerror = () => setIsListening(false);
    rec.onend = () => setIsListening(false);
    recognitionRef.current = rec;
    rec.start();
    setIsListening(true);
  }, [activeLang]);

  const stopListening = useCallback(() => {
    recognitionRef.current?.stop();
    setIsListening(false);
  }, []);

  // ── CV Upload ──────────────────────────────────────────────────────────────
  const handleFileUpload = useCallback(async (file: File) => {
    const allowed = ["application/pdf", "text/plain", "application/msword", "application/vnd.openxmlformats-officedocument.wordprocessingml.document"];
    if (!allowed.includes(file.type) && !file.name.endsWith(".txt") && !file.name.endsWith(".pdf")) {
      setMessages(prev => [...prev, { sender: "ai", text: "⚠️ Please upload a PDF, Word, or .txt file." }]);
      return;
    }
    setMessages(prev => [
      ...prev,
      { sender: "user", text: `📄 Uploading CV: ${file.name}...` },
      { sender: "ai", isLoading: true },
    ]);
    setIsLoading(true);
    const reader = new FileReader();
    reader.onload = async (e) => {
      const cvText = ((e.target?.result as string) || "").substring(0, 1500);
      if (!cvText.trim() || cvText.trim().length < 20) {
        setMessages(prev => [
          ...prev.filter(m => !m.isLoading),
          { sender: "ai", text: "⚠️ Could not read the file. Please upload a text-based PDF or .txt file." },
        ]);
        setIsLoading(false);
        return;
      }
      try {
        const res = await fetch("/api/predict", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({
            interests: cvText,
            experience_years_total: 2,
            education_level: "Bachelor",
            region,
          }),
        });
        const result = await res.json();
        if (result.success && result.recommendations?.length > 0) {
          setMessages(prev => [
            ...prev.filter(m => !m.isLoading),
            { sender: "ai", text: "✅ CV analyzed! Here are the best matching careers based on your profile:" },
            { sender: "ai", recommendations: result.recommendations },
          ]);
        } else {
          setMessages(prev => [
            ...prev.filter(m => !m.isLoading),
            { sender: "ai", text: "⚠️ Could not find matching careers from your CV. Try describing your interests manually." },
          ]);
        }
      } catch {
        setMessages(prev => [
          ...prev.filter(m => !m.isLoading),
          { sender: "ai", text: "⚠️ Could not connect to Flask. Make sure python app.py is running." },
        ]);
      } finally {
        setIsLoading(false);
      }
    };
    reader.onerror = () => {
      setMessages(prev => [...prev.filter(m => !m.isLoading), { sender: "ai", text: "⚠️ Failed to read file." }]);
      setIsLoading(false);
    };
    reader.readAsText(file);
  }, [region]);

  const translateToEnglish = (text: string): string => {
    const map: [RegExp, string][] = [
      [/برمج|كودينج|تكنولوج|كمبيوتر|حاسوب|برامج/g, "programming coding software"],
      [/ذكاء اصطناعي|تعلم آلي|بيانات/g, "artificial intelligence machine learning data science"],
      [/شبكات|سايبر|أمن معلومات/g, "networking cybersecurity"],
      [/تطبيقات|موبايل|جوال/g, "mobile app development"],
      [/ويب|مواقع/g, "web development"],
      [/تصميم|فنون|إبداع|رسم/g, "design art creative graphics"],
      [/معمار|هندسة مدنية/g, "architecture civil engineering"],
      [/طب|طبيب|صحة|مستشفى|تمريض/g, "medicine doctor health nursing"],
      [/صيدل/g, "pharmacy pharmacist"],
      [/أعمال|تجارة|إدارة|مشاريع/g, "business management entrepreneurship"],
      [/محاسب|مال|اقتصاد|بنك/g, "accounting finance economics banking"],
      [/تسويق|مبيعات/g, "marketing sales"],
      [/تعليم|تدريس|معلم/g, "teaching education teacher"],
      [/قانون|محام/g, "law lawyer legal"],
      [/هندسة كهرب/g, "electrical engineering"],
      [/هندسة ميكانيك/g, "mechanical engineering"],
      [/هندسة/g, "engineering"],
      [/علوم|بحث علمي/g, "science research"],
      [/بيئة|طبيعة/g, "environment nature"],
      [/إعلام|صحافة|أخبار/g, "media journalism news"],
      [/فيديو|أفلام|سينما/g, "video film cinema"],
      [/موسيق/g, "music"],
      [/پروگرامنگ|کوڈنگ|سافٹ ویئر/g, "programming coding software"],
      [/ڈیزائن|تخلیق/g, "design creative"],
      [/طب|ڈاکٹر|صحت/g, "medicine doctor health"],
      [/تعلیم|استاد/g, "teaching education"],
      [/کاروبار|تجارت/g, "business management"],
      [/ٹیکنالوجی|کمپیوٹر/g, "technology computer"],
      [/أحب|أستمتع|اهتمامي|أعمل في/g, "I love I enjoy interested in"],
      [/مجال/g, "field"],
    ];
    let result = text;
    for (const [pattern, replacement] of map) {
      result = result.replace(pattern, replacement);
    }
    return result.trim() || text;
  };

  const getExperience = (text: string) => {
    const m = text.match(/(\d+)\s*(year|yr|years)/i);
    return m ? parseInt(m[1]) : 2;
  };
  const getEducation = (text: string) => {
    const l = text.toLowerCase();
    if (l.includes("phd")) return "PhD";
    if (l.includes("master")) return "Master";
    if (l.includes("diploma")) return "Associate";
    return "Bachelor";
  };

  const handleSend = async () => {
    if (!input.trim() || isLoading) return;
    const userText = input.trim();
    setInput("");
    setMessages(prev => [...prev, { sender: "user", text: userText }]);

    const { reply: stReply, newState, langSwitch } = getSmallTalkReply(userText, convState, activeLang);
    const newLang = langSwitch ?? activeLang;
    if (langSwitch) setActiveLang(langSwitch);

    const cleanText = userText
      .replace(/use arabic|switch to arabic|استخدم العربية|تكلم عربي|بالعربي/gi, "")
      .replace(/use urdu|switch to urdu|اردو میں|اردو استعمال|اردو بولو/gi, "")
      .replace(/use english|switch to english|speak english|english please/gi, "")
      .replace(/,\s*$/, "").trim();

    if (stReply && cleanText.length < 3) {
      setConvState(newState);
      setTimeout(() => setMessages(prev => [...prev, { sender: "ai", text: stReply }]), 400);
      return;
    }

    if (stReply && !langSwitch) {
      setConvState(newState);
      setTimeout(() => setMessages(prev => [...prev, { sender: "ai", text: stReply }]), 400);
      return;
    }

    if (langSwitch && cleanText.length >= 3) {
      setTimeout(() => setMessages(prev => [...prev, { sender: "ai", text: stReply! }]), 400);
    }

    setConvState("idle");
    setIsLoading(true);
    setMessages(prev => [...prev, { sender: "ai", isLoading: true }]);

    try {
      const searchText = cleanText.length >= 3 ? cleanText : userText;
      const flaskText = translateToEnglish(searchText);
      const res = await fetch("/api/predict", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          interests: flaskText,
          experience_years_total: getExperience(searchText),
          education_level: getEducation(searchText),
          region,
        }),
      });
      const result = await res.json();
      if (result.success && result.recommendations?.length > 0) {
        setMessages(prev => [...prev.filter(m => !m.isLoading), { sender: "ai", recommendations: result.recommendations }]);
      } else {
        const lang = detectLanguage(userText);
        const errMsg =
          lang === "ar" ? "⚠️ لم أجد مهناً مطابقة. حاول أن تكون أكثر تحديداً." :
          lang === "ur" ? "⚠️ مجھے کوئی میل کھاتا کیریئر نہیں ملا۔ براہ کرم مزید تفصیل دیں۔" :
          "⚠️ I couldn't find matching careers. Try being more specific.";
        setMessages(prev => [...prev.filter(m => !m.isLoading), { sender: "ai", text: errMsg }]);
      }
    } catch {
      setMessages(prev => [
        ...prev.filter(m => !m.isLoading),
        { sender: "ai", text: "⚠️ Could not connect to the AI model.\nMake sure Flask is running:\n\npython app.py" },
      ]);
    } finally {
      setIsLoading(false);
    }
  };

  const isRTL = activeLang !== "en";

  return (
    <main className={`h-screen flex flex-col transition-all duration-300 relative ${dark ? "text-white" : "text-gray-900"}`}>
      <AnimatedBackground dark={dark} />

      {/* ── HEADER ── */}
      <div className={`relative z-10 flex-shrink-0 px-6 py-3 border-b backdrop-blur-xl transition-all ${dark ? "bg-[#080812]/80 border-gray-800/60" : "bg-white/80 border-gray-300/60"}`}>
        <div className="flex items-center justify-between max-w-5xl mx-auto">
          <div className="flex gap-1">
            {([["user", "👤 User"], ["admin", "⚙️ Admin"], ["client", "🏢 Client"]] as [DashboardView, string][]).map(([v, label]) => (
              <button key={v}
                onClick={() => {
                  if (v === "admin" || v === "client") {
                    setPendingView(v);
                    setPasswordInput("");
                    setPasswordError("");
                    setShowPasswordModal(true);
                  } else {
                    setShowPasswordModal(false);
                    setPasswordInput("");
                    setPasswordError("");
                    setView(v);
                  }
                }}
                className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-all border
                  ${(showPasswordModal ? pendingView === v : view === v)
                    ? dark ? "bg-indigo-600/80 border-indigo-500 text-white" : "bg-indigo-600 border-indigo-500 text-white"
                    : dark ? "bg-[#1a1a2e]/60 border-gray-700 text-gray-400 hover:text-white" : "bg-white/60 border-gray-200 text-gray-500 hover:text-black"}`}>
                {label}
              </button>
            ))}
          </div>
          <div className="text-center hidden sm:block">
            <h1 className="text-lg font-bold">Career Journey AI</h1>
            <p className={`text-xs ${dark ? "text-gray-400" : "text-gray-500"}`}>Vision 2030 🇸🇦🇦🇪 · Vision 2035 🇵🇰</p>
          </div>
          <div className="flex items-center gap-3">
            {view === "user" && (
              <div className="flex flex-col items-end">
                <select value={region} onChange={e => setRegion(e.target.value)}
                  className={`text-xs px-2 py-1.5 rounded-lg border outline-none cursor-pointer ${dark ? "bg-[#1a1a2e] border-gray-700 text-indigo-300" : "bg-white border-gray-300 text-indigo-600"}`}>
                  {REGIONS.map(r => <option key={r.value} value={r.value}>{r.label}</option>)}
                </select>
                <span className={`text-[10px] mt-0.5 ${dark ? "text-gray-500" : "text-gray-400"}`}>
                  {selectedRegion.currency} · {selectedRegion.vision} · affects salary & results
                </span>
              </div>
            )}
            <div className={`flex items-center gap-1 p-1 rounded-xl border ${dark ? "bg-[#1a1a2e]/80 border-gray-700" : "bg-gray-100 border-gray-300"}`}>
              <button onClick={() => setDark(false)} className={`p-1.5 rounded-lg transition-all ${!dark ? "bg-white text-black shadow" : "text-gray-400 hover:text-white hover:bg-[#2a2a4a]"}`}><Sun size={14} /></button>
              <button onClick={() => setDark(true)} className={`p-1.5 rounded-lg transition-all ${dark ? "bg-indigo-900/80 text-white shadow" : "text-gray-500 hover:text-black hover:bg-gray-200"}`}><Moon size={14} /></button>
            </div>
          </div>
        </div>
      </div>

      {/* Admin / Client */}
      {view === "admin" && !showPasswordModal && <div className="relative z-10 flex-1 overflow-y-auto"><AdminDashboard dark={dark} /></div>}
      {view === "client" && !showPasswordModal && <div className="relative z-10 flex-1 overflow-y-auto"><ClientDashboard dark={dark} /></div>}

      {/* ── USER CHAT ── */}
      {view === "user" && !showPasswordModal && (
        <>
          <div className="relative z-10 flex-1 overflow-y-auto px-6 py-6">
            {messages.length === 0 && (
              <div className="max-w-3xl mx-auto text-center mt-8">
                <h2 className={`text-3xl font-bold mb-3 ${dark ? "text-white" : "text-gray-900"}`}>What are your passions?</h2>
                <p className={`text-base leading-relaxed mb-1 ${dark ? "text-gray-400" : "text-gray-500"}`}>
                  Describe your interests in <span className="text-indigo-400 font-semibold">English</span>, <span className="text-yellow-400 font-semibold">Arabic</span> or <span className="text-green-400 font-semibold">Urdu</span>
                </p>
                <p className={`text-sm mb-5 ${dark ? "text-gray-500" : "text-gray-400"}`}>
                  Results aligned with <span className="text-green-500 font-semibold">{selectedRegion.vision}</span> · Salaries in <strong>{selectedRegion.currency}</strong>
                </p>
                <div className="grid grid-cols-1 gap-2 text-left max-w-xl mx-auto">
                  {[
                    "I love helping people and saving lives",
                    "أحب البرمجة وتطوير التطبيقات",
                    "مجھے ڈیزائن اور تخلیق پسند ہے",
                    "I enjoy nature, wildlife and the environment",
                  ].map((s, i) => (
                    <button key={i} onClick={() => setInput(s)}
                      className={`flex items-center gap-3 p-3.5 rounded-2xl border text-left transition-all backdrop-blur-sm
                        ${dark ? "bg-[#13131f]/60 border-gray-700/60 hover:border-indigo-500/50 hover:bg-[#1e1e3a]/70" : "bg-white/60 border-gray-200 hover:border-indigo-400 hover:bg-gray-50"}`}>
                      <Brain size={15} className="text-indigo-400 shrink-0" />
                      <span className={`text-sm ${dark ? "text-gray-300" : "text-gray-700"}`} dir={detectLanguage(s) !== "en" ? "rtl" : "ltr"}>{s}</span>
                    </button>
                  ))}
                </div>
                <p className={`mt-4 text-xs ${dark ? "text-gray-600" : "text-gray-400"}`}>
                  💡 Say &quot;use arabic&quot; or &quot;use urdu&quot; to switch language · 🎤 Voice input supported · 📄 Upload your CV
                </p>
              </div>
            )}
            <div className="flex flex-col gap-4 w-full max-w-3xl mx-auto">
              {messages.map((msg, i) => (
                <div key={i} className={`flex ${msg.sender === "user" ? "justify-end" : "justify-start"}`}>
                  {msg.sender === "user" ? (
                    <div className="bg-indigo-600 text-white px-5 py-3 rounded-2xl rounded-tr-sm max-w-[75%] text-sm shadow-lg shadow-indigo-900/20"
                      dir={detectLanguage(msg.text || "") !== "en" ? "rtl" : "ltr"}>
                      {msg.text}
                    </div>
                  ) : msg.isLoading ? (
                    <div className={`px-5 py-4 rounded-2xl rounded-tl-sm border flex items-center gap-3 backdrop-blur-md ${dark ? "bg-[#13131f]/70 border-gray-700/60" : "bg-white/70 border-gray-300"}`}>
                      <Loader2 size={16} className="animate-spin text-indigo-400" />
                      <span className={`text-sm ${dark ? "text-gray-400" : "text-gray-500"}`}>Searching careers across UAE, KSA & Pakistan...</span>
                    </div>
                  ) : msg.recommendations ? (
                    <div className={`rounded-2xl rounded-tl-sm border p-5 max-w-[95%] w-full backdrop-blur-md ${dark ? "bg-[#13131f]/70 border-gray-700/60" : "bg-white/70 border-gray-300"}`}>
                      <RecommendationsCard recommendations={msg.recommendations} dark={dark} />
                    </div>
                  ) : (
                    <div className={`px-5 py-4 rounded-2xl rounded-tl-sm border max-w-[75%] text-sm whitespace-pre-line backdrop-blur-md ${dark ? "bg-[#13131f]/70 border-gray-700/60 text-gray-200" : "bg-white/70 border-gray-300 text-gray-800"}`}
                      dir={detectLanguage(msg.text || "") !== "en" ? "rtl" : "ltr"}>
                      {msg.text}
                    </div>
                  )}
                </div>
              ))}
              <div ref={messagesEndRef} />
            </div>
          </div>

          {/* ── INPUT BAR ── */}
          <div className={`relative z-10 flex-shrink-0 px-6 py-4 border-t backdrop-blur-xl transition-all ${dark ? "bg-[#080812]/70 border-gray-800/60" : "bg-white/70 border-gray-300/60"}`}>
            <div className={`max-w-5xl mx-auto rounded-[30px] flex items-center px-5 py-3 shadow-2xl border transition-all ${dark ? "bg-[#1a1a2e]/80 border-gray-700/60" : "bg-white border-gray-300"}`}>
              <label
                className={`cursor-pointer p-2.5 rounded-2xl transition-all ${dark ? "text-gray-400 hover:text-white hover:bg-[#2a2a4a]" : "text-gray-500 hover:text-black hover:bg-gray-200"}`}
                title="Upload CV (PDF/TXT)">
                <Paperclip size={20} strokeWidth={2.2} />
                <input
                  ref={fileInputRef}
                  type="file"
                  accept=".pdf,.txt,.doc,.docx"
                  className="hidden"
                  onChange={e => {
                    if (e.target.files?.[0]) {
                      handleFileUpload(e.target.files[0]);
                      e.target.value = "";
                    }
                  }}
                />
              </label>
              <input
                type="text"
                placeholder={
                  activeLang === "ar" ? "صف اهتماماتك..." :
                  activeLang === "ur" ? "اپنی دلچسپیاں لکھیں..." :
                  "Describe your interests... / اكتب اهتماماتك... / اپنی دلچسپیاں لکھیں..."
                }
                value={input}
                onChange={e => setInput(e.target.value)}
                onKeyDown={e => e.key === "Enter" && handleSend()}
                disabled={isLoading}
                dir={isRTL ? "rtl" : "ltr"}
                className={`flex-1 bg-transparent outline-none px-4 text-base ${dark ? "placeholder-gray-600 text-white" : "placeholder-gray-400 text-black"}`}
              />
              <button
                onClick={isListening ? stopListening : startListening}
                className={`p-2.5 rounded-2xl mr-1 transition-all ${isListening ? "bg-red-500/20 text-red-400 animate-pulse" : dark ? "text-gray-400 hover:text-white hover:bg-[#2a2a4a]" : "text-gray-500 hover:text-black hover:bg-gray-200"}`}
                title={isListening ? "Stop listening" : "Voice input"}>
                {isListening ? <MicOff size={20} strokeWidth={2.2} /> : <Mic size={20} strokeWidth={2.2} />}
              </button>
              <button
                onClick={handleSend}
                disabled={isLoading || !input.trim()}
                className="p-2.5 rounded-2xl transition-all disabled:opacity-40 disabled:cursor-not-allowed bg-indigo-600 hover:bg-indigo-500 text-white">
                {isLoading ? <Loader2 size={18} className="animate-spin" /> : <SendHorizontal size={18} strokeWidth={2.4} />}
              </button>
            </div>
            <p className={`text-center text-xs mt-2 ${dark ? "text-gray-600" : "text-gray-400"}`}>
              🎤 Voice · 📄 CV Upload · 🌍 UAE / KSA / Pakistan · 🗣️ EN / AR / UR · Powered by O*NET + ML
            </p>
          </div>
        </>
      )}

      {/* ── PASSWORD SCREEN (full page, renders inside layout) ── */}
      {showPasswordModal && (
        <div className="relative z-10 flex-1 flex items-center justify-center px-6">
          <div className="w-full max-w-md">
            {/* Icon + Title */}
            <div className="text-center mb-8">
              <div className={`inline-flex items-center justify-center w-20 h-20 rounded-3xl mb-5 text-4xl shadow-2xl border
                ${pendingView === "admin"
                  ? dark ? "bg-indigo-900/60 border-indigo-700/60" : "bg-indigo-50 border-indigo-200"
                  : dark ? "bg-emerald-900/60 border-emerald-700/60" : "bg-emerald-50 border-emerald-200"}`}>
                {pendingView === "admin" ? "⚙️" : "🏢"}
              </div>
              <h2 className={`text-2xl font-bold mb-2 ${dark ? "text-white" : "text-gray-900"}`}>
                {pendingView === "admin" ? "Admin Access" : "Client Access"}
              </h2>
              <p className={`text-sm ${dark ? "text-gray-400" : "text-gray-500"}`}>
                This area is protected. Enter the password to continue.
              </p>
            </div>

            {/* Password card */}
            <div className={`rounded-3xl border p-8 backdrop-blur-xl shadow-2xl
              ${dark ? "bg-[#13131f]/80 border-gray-700/60" : "bg-white/90 border-gray-200"}`}>

              <label className={`block text-xs font-bold uppercase tracking-widest mb-2
                ${dark ? "text-gray-400" : "text-gray-500"}`}>
                Password
              </label>
              <input
                type="password"
                placeholder="Enter password..."
                value={passwordInput}
                onChange={e => { setPasswordInput(e.target.value); setPasswordError(""); }}
                onKeyDown={e => { if (e.key === "Enter") handlePasswordUnlock(); }}
                className={`w-full px-5 py-4 rounded-2xl border outline-none text-base mb-3 transition-all
                  focus:ring-2 focus:ring-indigo-500/40
                  ${dark
                    ? "bg-[#0d0d1a] border-gray-700 text-white placeholder-gray-600 focus:border-indigo-500"
                    : "bg-gray-50 border-gray-300 text-black placeholder-gray-400 focus:border-indigo-400"}`}
                autoFocus
              />

              {/* Error message */}
              {passwordError && (
                <div className={`flex items-center gap-2 px-4 py-2.5 rounded-xl mb-4 text-sm
                  ${dark ? "bg-red-900/30 border border-red-800/50 text-red-400" : "bg-red-50 border border-red-200 text-red-600"}`}>
                  <span>⚠️</span> {passwordError}
                </div>
              )}

              {/* Buttons */}
              <div className="flex gap-3">
                <button
                  onClick={() => { setShowPasswordModal(false); setPasswordInput(""); setPasswordError(""); }}
                  className={`flex-1 py-3.5 rounded-2xl border text-sm font-semibold transition-all
                    ${dark ? "border-gray-700 text-gray-400 hover:text-white hover:border-gray-500 hover:bg-white/5" : "border-gray-300 text-gray-500 hover:text-black hover:bg-gray-50"}`}>
                  ← Back
                </button>
                <button
                  onClick={handlePasswordUnlock}
                  className={`flex-1 py-3.5 rounded-2xl text-white text-sm font-semibold transition-all shadow-lg
                    ${pendingView === "admin"
                      ? "bg-indigo-600 hover:bg-indigo-500 shadow-indigo-900/30"
                      : "bg-emerald-600 hover:bg-emerald-500 shadow-emerald-900/30"}`}>
                  Unlock 🔓
                </button>
              </div>
            </div>

            {/* Hint */}
            <p className={`text-center text-xs mt-4 ${dark ? "text-gray-700" : "text-gray-400"}`}>
              {pendingView === "admin" ? "Admin password required for system access" : "Client password required for employer view"}
            </p>
          </div>
        </div>
      )}

    </main>
  );
}