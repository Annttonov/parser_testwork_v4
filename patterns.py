import re

TASK_RE = re.compile(r"^(\d{1,2}|\w)+?\)\s")

CHAPTER_RE = re.compile(r"(^[А-ЯЁA-Z]-\d+\*?.)+?\s.*")

TASK_NUMBER_RE = re.compile(r"^\(?(\d)\)?$")

VAR_RE = re.compile(r"[B|В][a|а][p|р][u|и][a|а]нт",
                    re.IGNORECASE)

LEVEL_RE = re.compile(r"^[у|y][p|р][o|о]в[e|е]н[b|ь]\s.?(\w).?$",
                      re.IGNORECASE)
