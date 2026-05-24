Use two separate built-in Azure Speech voices:

* de-DE-Florian:DragonHDLatestNeural for German
*ru-RU-DmitryNeural for Russian. 

That gives a natural male German HD voice and a native male Russian voice, while keeping the full Azure Speech pronunciation toolchain for nautical terms.

Create a Foundry resource with Speech enabled, optionally create a Foundry project for portal use, and then call the Speech service with the selected voice name.

Use Azure Speech with the Speech SDK, not the Azure OpenAI TTS API.

Reasons:

* pronunciation control for nautical terminology.
* German and Russian, not just one multilingual voice.
* Azure Speech supports SSML, aliases, say-as, sub, phonemes, and custom lexicons.

What To Create In Azure:
* Azure subscription.
* Resource group.
* One Microsoft Foundry resource of kind AIServices.
* One Foundry project inside that resource if you want to use the Foundry portal playgrounds and organize assets.

Parameters:
* Region: swedencentral
* REST synthesis endpoint: https://swedencentral.tts.speech.microsoft.com/cognitiveservices/v1
* API key: ECLwV***
It loads SPEECH_KEY, SPEECH_REGION, TTS_VOICE_DE, TTS_VOICE_RU, and TTS_OUTPUT_FORMAT from the environment or from env.sh

Execution:
Generate SSML questions script:
```
python3 app/questions-tts/generate_questions_ssml.py \
	--input data/questions.json \
	--output data/questions-tts/questions-all-tts.xml
```

Input parameters for the generator:
* `--input`: source JSON file, default `data/questions.json`
* `--output`: target SSML XML file, default `data/questions-tts/questions-all-tts.xml`
* `--chapter`, `--from-number`, `--to-number`, `--limit`: optional filters

Generate audio:
```
source ~/pyvenv/bin/activate
cd app/questions-tts
python3 -m pip install -r requirements.txt
python3 synthesize_questions.py <ssml-xml-file> --insecure

# example
python3 synthesize_questions.py ../../data/questions-tts/questions-all-tts.xml --insecure
```
Note: `insecure` option is used to circumvent Zscaler messing with the local machine certificates.

To generate a range:
```
python3 app/questions-tts/generate_questions_ssml.py --from-number 40 --to-number 60 --output data/questions-tts/questions-040-060.xml
```

To synthesize that range:
```
cd app/questions-tts
python3 synthesize_questions.py ../../data/questions-tts/questions-040-060.xml --insecure
```