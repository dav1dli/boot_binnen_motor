```
chapter-08.json (source of truth)
       │
       ├──► Azure OpenAI (GPT-4o) ──► Slide deck (reveal.js / PPTX)
       │       • prompt: "Generate N slides from sections, use key_points as bullets"
       │       • presenter notes = full text blocks
       │       • images referenced by src
       │
       ├──► Azure Speech TTS ──► MP3 per section per language
       │       • input: text blocks → SSML (reuse generate_questions_ssml.py pattern)
       │       • output: audio/chapters/08/08-01-hoch-tief.de.mp3, .ru.mp3 …
       │
       ├──► Azure OpenAI ──► Quiz JSON (MCQ from terms + text)
       │       • prompt: "From each section, create 3 multiple-choice questions"
       │       • feed into existing showquestion app
       │
       ├──► Azure OpenAI ──► Flashcards JSON (from terms array)
               • front: term in language A, back: definition in language B
               • reversible for vocabulary drills
```

To add:
* generate_chapter_ssml.py — SSML generator, but reads chapter-XX.json and emits per-section SSML files
* generate_slides.py — sends chapter JSON + a system prompt to Azure OpenAI, outputs a reveal.js HTML or PPTX
* generate_quiz.py — sends sections + terms to Azure OpenAI, outputs quiz JSON compatible with the showquestion app
* synthesize_chapter.py	SSML batch XML	MP3 per section per language	Azure Speech (env.sh)
Audio files are separate per language, named chapter-08-01-de.mp3, chapter-08-01-ru.mp3, etc.


```
# 1. Generate SSML
python3 scripts/generate_chapter_ssml.py data/chapter-08.json -o data/chapter-08-tts.xml

# 2. Synthesize audio (separate DE and RU files)
python3 scripts/synthesize_chapter.py data/chapter-08-tts.xml --insecure --env-file scripts/env.sh

# 3. Generate slide decks (one per language)
python3 scripts/generate_slides.py data/chapter-08.json --lang de
python3 scripts/generate_slides.py data/chapter-08.json --lang ru

# 4. Generate quiz (needs AOAI_ENDPOINT, AOAI_KEY, AOAI_DEPLOYMENT in env.sh)
python3 scripts/generate_quiz.py data/chapter-08.json --lang de --count 10
```

The slides reference audio files via audio/chapters/chapter-08-{slide}-{lang}.mp3 and include speaker notes from the full text blocks. For the quiz generator, add AOAI_ENDPOINT, AOAI_KEY, and AOAI_DEPLOYMENT to env.sh.