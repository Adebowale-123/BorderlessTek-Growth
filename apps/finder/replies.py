"""
Drafts a reply to a parent's public post: genuinely useful advice first, then an honest disclosure and an invitation.

Every draft is reviewed and posted by a person. Communities welcome helpful answers and remove pure ads, and
being open about who we are keeps BorderlessTek trusted (and within platform rules).
"""

import hashlib
from urllib.parse import urlencode, urlparse, urlunparse, parse_qsl

PATHS = {  # (skill, age band) -> a sensible next step, in plain words
    ("coding", "young"): "Scratch Jr and then Scratch: drag-and-drop blocks that teach real logic (loops, events) "
                         "without typing getting in the way",
    ("coding", "middle"): "Scratch for a few months to learn the logic, then a gentle move into Python",
    ("coding", "teen"): "Python or JavaScript, building small real projects (a game, a website) rather than only "
                        "doing exercises",
    ("scratch", "young"): "Scratch Jr first, then full Scratch once reading is comfortable",
    ("scratch", "middle"): "building their own Scratch games, then moving to Python when they hit Scratch's limits",
    ("scratch", "teen"): "moving from Scratch to Python, where the same logic carries straight over",
    ("python", "young"): "starting with Scratch first; Python's typing usually clicks better from about 9 or 10",
    ("python", "middle"): "Python with turtle graphics or simple games, so they see results quickly",
    ("python", "teen"): "Python projects they care about: a game, a bot, or a small data project",
    ("game design", "young"): "making simple games in Scratch, which builds the same thinking as 'real' game engines",
    ("game design", "middle"): "Scratch games, then Roblox Studio (Lua) if they already love Roblox",
    ("game design", "teen"): "Roblox Studio or Godot/Unity, finishing small games rather than starting huge ones",
    ("animation", "young"): "stop-motion apps and simple frame-by-frame drawing: great for storytelling",
    ("animation", "middle"): "2D animation (Krita or similar) and then the basics of 3D in Blender",
    ("animation", "teen"): "Blender for 3D: free, used in industry, and amazing for a portfolio",
    ("design", "young"): "playful digital drawing and simple layouts in Canva",
    ("design", "middle"): "Canva for layouts, then the basics of colour, typography and composition",
    ("design", "teen"): "Figma and real design briefs (a poster, an app screen) to build a portfolio",
    ("robotics", "young"): "screen-free coding toys and then a BBC micro:bit",
    ("robotics", "middle"): "the BBC micro:bit or LEGO Spike, programmed with blocks and then Python",
    ("robotics", "teen"): "Arduino or Raspberry Pi projects that mix electronics with Python",
    ("AI", "young"): "unplugged activities about how computers 'learn' plus simple Scratch AI extensions",
    ("AI", "middle"): "Machine Learning for Kids projects (they train a model and use it in Scratch)",
    ("AI", "teen"): "Python first, then beginner machine-learning projects",
    ("STEM", "young"): "Scratch Jr and hands-on building toys",
    ("STEM", "middle"): "Scratch plus a micro:bit: coding they can see and touch",
    ("STEM", "teen"): "Python plus a project in an area they love (games, music, robots)",
}
FREE = {
    "coding": "the free Scratch website (scratch.mit.edu) and code.org are brilliant places to start",
    "scratch": "scratch.mit.edu has free tutorials and a huge library of projects to remix",
    "python": "free tools like Trinket or the Raspberry Pi Foundation's projects site are great for first steps",
    "game design": "scratch.mit.edu is a great free start, and Roblox Studio is free too",
    "animation": "Blender and Krita are both free",
    "design": "Canva is free to start with",
    "robotics": "the micro:bit website has free projects you can try in the browser",
    "AI": "machinelearningforkids.co.uk is free",
    "STEM": "code.org and scratch.mit.edu are both free",
}
OPENERS = [
    "That's brilliant that {who} is interested in {topic}!",
    "Lovely question, and great that {who} is keen on {topic}.",
    "{Topic} is such a good skill for {who} to explore.",
    "It's great you're supporting {who} with {topic}.",
]
WHY_LIVE = [
    "What makes the biggest difference at this age is a real person giving feedback and keeping it fun, so "
    "they finish projects instead of drifting off.",
    "Small live classes tend to work best: they get help the moment they're stuck, and having others to show "
    "their work to keeps motivation high.",
    "A mix of structure and creative freedom works well: short lessons, then their own project ideas.",
]


def band(age):
    if age is None:
        return "middle"
    return "young" if age <= 8 else "middle" if age <= 12 else "teen"


def tracked(url, source):
    """Add tracking tags to the booking link so you can see which posts bring families."""
    if not url:
        return ""
    parts = urlparse(url)
    query = dict(parse_qsl(parts.query))
    query.update({"utm_source": source or "community", "utm_medium": "reply", "utm_campaign": "lead-finder"})
    return urlunparse(parts._replace(query=urlencode(query)))


def draft(signals, *, company="BorderlessTek", name="", booking_url="", source="community", seed=""):
    """A friendly, useful reply. `seed` makes the wording vary from post to post but stay the same for one post."""
    pick = int(hashlib.md5((seed or "x").encode()).hexdigest(), 16)
    skills = signals.get("skills") or ["coding"]
    skill = skills[0] if skills[0] in FREE else "coding"
    ages = [a for a in signals.get("ages") or [] if 6 <= a <= 16]
    age = ages[0] if ages else None
    who = f"your {age}-year-old" if age else "your child"
    topic = {"STEM": "STEM", "AI": "AI"}.get(skill, skill)
    opener = OPENERS[pick % len(OPENERS)].format(who=who, topic=topic, Topic=topic[:1].upper() + topic[1:])
    path = PATHS.get((skill, band(age)), PATHS[("coding", band(age))])
    lines = [
        opener,
        f"{'At that age' if age else 'For most kids'}, a good path is {path}.",
        f"To try things out first, {FREE[skill]}.",
        WHY_LIVE[pick // 7 % len(WHY_LIVE)],
    ]
    link = tracked(booking_url, source)
    disclosure = (f"(Full disclosure: I work with {company}. We run small live online classes in coding, animation "
                  f"and design for ages 6–16, and families join from the UK, Europe, North America and Australia.")
    disclosure += f" If it would help, you can book a free chat with our team here: {link})" if link else \
        " Happy to share more if it's useful.)"
    lines.append(disclosure)
    lines.append(f"Good luck — {name}" if name else "Good luck!")
    return "\n\n".join(lines)


FOLLOW_UPS = [
    "Hi {name}, just checking you saw my earlier message about {topic} for {who}. Happy to answer any questions, "
    "or you can pick a time for a quick chat with our team here: {link}",
    "Hi {name}, I thought this might help: lots of parents tell us the hardest part is finding something {who} "
    "sticks with. Our onboarding call is free and takes 15 minutes. We'll suggest the right class for their age "
    "and interests: {link}",
    "Hi {name}, I won't keep messaging. If {topic} classes for {who} become a priority later, our door is always "
    "open: {link}. Wishing you and your family all the best!",
]


def follow_up(count, *, name="", topic="coding", age=None, link=""):
    """The message for the next follow-up (gentle, then helpful, then a polite last note)."""
    template = FOLLOW_UPS[min(count, len(FOLLOW_UPS) - 1)]
    return template.format(name=name or "there", topic=topic or "coding",
                           who=f"your {age}-year-old" if age else "your child", link=link or "(booking link)")
