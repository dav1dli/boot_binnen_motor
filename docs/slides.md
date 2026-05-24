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
* generate_chapter_ssml.py — like the existing question SSML generator, but reads chapter-XX.json and emits per-section SSML files
* generate_slides.py — sends chapter JSON + a system prompt to Azure OpenAI, outputs a reveal.js HTML or PPTX
* generate_quiz.py — sends sections + terms to Azure OpenAI, outputs quiz JSON compatible with the showquestion app