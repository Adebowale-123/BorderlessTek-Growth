"""
Scores a public post (0–100) for how likely it is a parent looking for digital-skills learning for a child aged 6–16.

  Parent / child context   25   ("my son", "my 9 year old", "our daughter", "homeschool")
  Child aged 6–16          15   (an age outside 6–16 costs points)
  Topic                    20   (coding, Scratch, Python, Roblox Studio, animation, design, robotics, STEM…)
  Looking for help         25   ("looking for", "recommend", "any suggestions", "where can", "worth it"…)
  Learning format          10   (online, class, course, tutor, club, camp, lessons)
  Target country            5   (UK, US, Canada, Australia, Europe mentions)

Posts with no sign of a parent or a child are capped below the usual threshold, so adults learning to code for
themselves (and children posting about themselves) don't show up. Job ads and selling posts are pushed out.
"""

import re

SKILLS = {
    "coding": r"\b(coding|coder|programming|programmer|computer science|comp ?sci|learn(?:ing)? to code|write code|"
              r"code club|codecademy|javascript|html|css|web ?dev(?:elopment)?|app (?:dev|development|making))\b",
    # "Scratch" only in a coding sense: not "from scratch" or "scratch card".
    "scratch": r"\bscratch ?(?:jr|junior|programming|coding|projects?|games?|website|account|studio)\b|\bscratch\.mit\b|"
               r"\b(?:on|in|using|with|learn(?:ing|s)?|loves?|likes?|does|uses) scratch\b",
    "python": r"\bpython\b",
    "game design": r"\b(game (?:design|dev(?:elopment)?|making|maker)|make (?:their|his|her) own games?|roblox studio|"
                   r"unity|godot|minecraft (?:mod(?:ding|s)?|education|coding))\b",
    "animation": r"\b(animation|animating|animate|stop[- ]motion|blender|3d model(?:ling|ing)?)\b",
    "design": r"\b(graphic design|digital art|drawing (?:app|tablet)|procreate|canva|figma|ui/?ux|digital design)\b",
    "robotics": r"\b(robotics|robots?|micro:?bit|arduino|raspberry pi|lego (?:mindstorms|spike))\b",
    "AI": r"\b(artificial intelligence|machine learning|\bai\b for kids|chatgpt for kids)\b",
    "STEM": r"\b(stem|steam|tech(?:nology)? skills|digital skills)\b",
}
PARENT = re.compile(
    r"\b(my|our) (son|daughter|kid|kids|child|children|boy|girl|teen|teenager|tween|little one|"
    r"\d{1,2} ?(?:yo|y/o|year[- ]old))\b|\b(ds|dd)\b|\bhome ?school(?:ing|er)?\b|\bas a (?:mum|mom|dad|parent)\b|"
    r"\b(?:mum|mom|dad|parent)s? (?:here|of)\b|\bfor (?:my|our) (?:kids?|children)\b")
AGE = re.compile(r"\b(\d{1,2}) ?(?:yo|y/o|y\.o\.|years? old|year[- ]old|yr[- ]old|yrs? old)\b|\baged? (\d{1,2})\b|"
                 r"\b(\d{1,2})(?:-| to )\d{1,2} (?:year[- ]olds|yos)\b")
SCHOOL_YEAR = re.compile(r"\b(?:year|grade) (\d{1,2})\b")
INTENT = re.compile(
    r"\b(looking for|recommend(?:ation|ations|ed)?s?|suggestions?|advice|any (?:good|ideas|tips)|where (?:can|do|should)|"
    r"how (?:can|do|should) (?:i|we)|best (?:way|online|place|course|class|classes|program|programme|camp|app|site)|"
    r"anyone (?:tried|used|know|recommend)|worth (?:it|the money)|ideas for|help (?:me )?(?:find|choose)|"
    r"wants? to learn|interested in (?:learning|coding)|get (?:him|her|them) into|should (?:i|we) (?:sign|enrol|enroll))\b")
FORMAT = re.compile(r"\b(online|virtual|class(?:es)?|course|lessons?|tutor(?:s|ing)?|club|camp|after[- ]school|"
                    r"programme|program|bootcamp|school holidays?|summer)\b")
COUNTRY = re.compile(r"\b(uk|united kingdom|england|scotland|wales|london|us|usa|united states|america|canada|"
                     r"canadian|australia|aussie|europe|ireland|germany|france|netherlands|spain)\b")
NEGATIVE = re.compile(r"\[(?:hiring|for hire|selling|offer)\]|\b(we are hiring|job opening|salary|for sale|"
                      r"use my code|promo code|discount code|affiliate)\b")
ADULT = re.compile(r"\b(i'?m|i am) (?:\d{2})\b|\bcareer change\b|\bmy (?:job|career|resume|cv)\b|\bfor myself\b|"
                   r"\b(?:junior|senior) developer\b|\bbootcamp for me\b")


def detect(text):
    """Pull out what the post is about: skills, child's age, and the signals behind the score."""
    t = (text or "").lower()
    skills = [name for name, pattern in SKILLS.items() if re.search(pattern, t)]
    ages = []
    for m in AGE.finditer(t):
        value = next((g for g in m.groups() if g), None)
        if value:
            ages.append(int(value))
    for m in SCHOOL_YEAR.finditer(t):  # UK "Year 5" is about age 9-10; US grade 5 is about age 10-11
        ages.append(int(m.group(1)) + 5)
    ages = [a for a in ages if 2 <= a <= 25]
    return {"skills": skills, "ages": sorted(set(ages)), "parent": bool(PARENT.search(t)),
            "intent": bool(INTENT.search(t)), "format": bool(FORMAT.search(t)),
            "country": bool(COUNTRY.search(t)), "negative": bool(NEGATIVE.search(t)), "adult": bool(ADULT.search(t))}


def score(text):
    """Return (score 0-100, signals dict)."""
    s = detect(text)
    points = 0
    reasons = []
    if s["parent"]:
        points += 25
        reasons.append("A parent talking about their child")
    in_range = [a for a in s["ages"] if 6 <= a <= 16]
    if in_range:
        points += 15
        reasons.append(f"Child aged {in_range[0]}")
    elif s["ages"]:
        points -= 15
        reasons.append("Age outside 6–16")
    if s["skills"]:
        points += 20
        reasons.append("About " + ", ".join(s["skills"][:3]))
    if s["intent"]:
        points += 25
        reasons.append("Asking for recommendations")
    if s["format"]:
        points += 10
        reasons.append("Interested in classes or courses")
    if s["country"]:
        points += 5
        reasons.append("Mentions a target country")
    if not s["parent"] and not in_range:  # probably an adult learner, or a child posting
        points = min(points, 35)
    if not s["skills"]:  # nothing about the digital skills we teach
        points = min(points, 30)
    if not s["intent"]:  # mentions it, but isn't asking for help: worth a look, never "hot"
        points = min(points, 55)
    if s["adult"]:
        points = min(points - 25, 30)
        reasons.append("Sounds like an adult learner")
    if s["negative"]:
        points -= 40
        reasons.append("Looks like an ad or a job post")
    s["reasons"] = reasons
    return max(0, min(100, points)), s
