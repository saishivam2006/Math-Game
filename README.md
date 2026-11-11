# Math Quest — The Adventure of Numbers

A local, offline, single-player side-scrolling platform adventure for Classes 5–6. Run and jump through original themed trails, collect coins, avoid hazards, and answer maths questions at golden gates. The flow adapts the attached Math Quest write-up's adventure, hints, retries, progress screen, local saving, and rewards to the requested age group and progression.

## Play

1. Install Python 3.10 or newer.
2. Open a terminal in this folder and run `py -m pip install -r requirements.txt`.
3. Start the game with `py math_quest.py`.

Enter an email ID and player name, then choose a trail. Use **← / →** or **A / D** to move; press **Space** or **↑** to jump. Collect coins and avoid thorn hazards on the way to the golden maths gate. Press **1–4** or click to answer, **H** for a hint, and **Esc** to return to the trail map. Wrong answers are safe and can be retried.

## Progression

The adventure has four stages, each with five short trails:

1. **Number Forest** — BODMAS and number skills.
2. **Fraction Falls** — fractions and sharing.
3. **Algebra Peaks** — missing numbers, patterns, and early algebra.
4. **Shape Sun Temple** — shapes and everyday maths.

Clear all five trails in a stage to earn its crystal and unlock the next stage. XP and coins reward completion; hints and retries do not remove health or block progress.

## Local profiles and learning data

The email field identifies a local player profile. This is an offline profile, not an email verification or password-based account; the game has no server and sends no data anywhere. Progress and answer records are stored in SQLite under `%LOCALAPPDATA%\MathQuest\mathquest.sqlite3` (or the user's home folder's `MathQuest` directory if `LOCALAPPDATA` is unavailable).

Each submitted answer records the stage, trail, topic, question, submitted and expected answer, correctness, response time for that attempt, attempt number, hint use, and timestamp. **My Progress** summarizes attempts, accuracy, average time, and stage completion. **Export Answers CSV** writes the signed-in local profile's records to `Documents\MathQuest\exports\math_quest_answers.csv` for analysis.

Because email IDs and children's learning records are personal data, this prototype keeps them on the device. If the project later needs a shared teacher dashboard, add a separate consent-based sync service and decide how profiles are authenticated and protected before collecting data across devices.

## Project prompt adaptation

The source write-up targets Classes 7–8 and recommends beginning with one Number Forest world and three playable levels. This build follows its Pygame/local-storage direction while adapting the target to Classes 5–6 and the requested four-stage, five-trail progression. It uses original characters, shapes, colors, and text.
