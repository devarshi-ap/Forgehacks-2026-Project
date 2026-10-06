# StormSignal test personas (QA)

QA = quality assurance: trying the app with realistic users to catch mistakes
before the judges do. Each persona is a made-up person (no real data).

## How to test each persona
1. Type the description into the intake screen.
2. Answer the follow-up questions.
3. Check every item in the checklist below. Write PASS or FAIL and a short note.

## Checks for every persona
- [ ] The amber safety banner is visible on all 3 screens (desktop and mobile)
- [ ] The follow-up questions make sense for this person
- [ ] The top 3 risks match the location
- [ ] The plan does NOT give advice that is unsafe for this person
- [ ] Every step has a source
- [ ] The checklist can be ticked and the progress bar updates
- [ ] If the verifier fails, the "rules-based version" message shows
- [ ] No page crashes if the answer is "Not sure" or "I don't know"

## Personas
| # | Persona | Location | What must be different from generic advice |
|---|---------|----------|---------------------------------------------|
| 1 | Lives alone, 3rd floor, powered wheelchair, lift needs electricity (the Figma example) | New York City, United States | No "use the lift" advice; backup charging; accessible way to leave; cool place; check-in |
| 2 | Family of 4 in a mobile home | (pick a storm region) | Leave the mobile home early; do not shelter in it during high wind |
| 3 | Person who uses an oxygen concentrator | (pick a region) | Plan for power loss; backup supply; know where to go early |
| 4 | Household with no car, elderly parent | (pick a region) | Evacuation help without driving; transport registration |

## Edge cases
- Empty location or description (should show an error, not crash)
- A very short description ("I live alone")
- A location the app does not know
- Answering every follow-up with "Not sure"
- Using the Back button and then continuing again
- Clicking "Start over" and running a different persona

## Results log
| Persona | Date | PASS/FAIL | Notes |
|---------|------|-----------|-------|
|         |      |           |       |

## Design checks (from the Figma guide)
- [ ] Amber is used ONLY for safety notices
- [ ] Selected radio, tab and step have a label or underline, not colour alone
- [ ] Buttons and inputs are at least 56px high; checkbox rows 48px+
- [ ] On a phone-width window the columns stack and the text does not shrink
- [ ] Every demo plan is labelled as illustrative
