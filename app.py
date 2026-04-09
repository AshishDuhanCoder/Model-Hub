from flask import Flask, render_template, jsonify, request
from dotenv import load_dotenv
import requests as http_requests
import urllib3
import re
import json
import os

# Load .env file (GEMINI_API_KEY and any future keys live there)
load_dotenv()

# Suppress SSL warnings — Windows often lacks system CA bundle in Python
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

_HTTP = http_requests.Session()
_HTTP.verify = False  # skip SSL verification for local dev on Windows

app = Flask(__name__)

# ---------------------------------------------------------------------------
# MODEL DATA  (O(1) category lookup via dict key)
# ---------------------------------------------------------------------------
MODELS = {
    "chat": [
        {
            "id": "gpt-4o", "name": "GPT-4o", "provider": "OpenAI", "category": "chat",
            "badge": "Most Popular", "badge_color": "gradient-blue",
            "description": "OpenAI's flagship multimodal model. Handles text, vision, and audio natively with state-of-the-art reasoning.",
            "tags": ["multimodal", "reasoning", "vision", "function-calling"],
            "pricing": "$5 / 1M input tokens", "context": "128k tokens", "status": "GA",
            "docs_url": "https://platform.openai.com/docs/models/gpt-4o",
            "snippet": {
                "python": "from openai import OpenAI\n\nclient = OpenAI(api_key='YOUR_API_KEY')\n\nresponse = client.chat.completions.create(\n    model='gpt-4o',\n    messages=[{'role': 'user', 'content': 'Hello!'}]\n)\nprint(response.choices[0].message.content)",
                "curl": "curl https://api.openai.com/v1/chat/completions \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"model\": \"gpt-4o\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}]}'",
                "js": "import OpenAI from 'openai';\n\nconst client = new OpenAI({ apiKey: 'YOUR_API_KEY' });\nconst response = await client.chat.completions.create({\n  model: 'gpt-4o',\n  messages: [{ role: 'user', content: 'Hello!' }],\n});\nconsole.log(response.choices[0].message.content);"
            }
        },
        {
            "id": "claude-3-5-sonnet", "name": "Claude 3.5 Sonnet", "provider": "Anthropic", "category": "chat",
            "badge": "Best Coding", "badge_color": "gradient-purple",
            "description": "Anthropic's most intelligent model, excelling at complex reasoning, coding, and nuanced analysis with a 200k context window.",
            "tags": ["reasoning", "coding", "analysis", "long-context"],
            "pricing": "$3 / 1M input tokens", "context": "200k tokens", "status": "GA",
            "docs_url": "https://docs.anthropic.com/en/docs/about-claude/models",
            "snippet": {
                "python": "import anthropic\n\nclient = anthropic.Anthropic(api_key='YOUR_API_KEY')\n\nmessage = client.messages.create(\n    model='claude-3-5-sonnet-20241022',\n    max_tokens=1024,\n    messages=[{'role': 'user', 'content': 'Hello!'}]\n)\nprint(message.content[0].text)",
                "curl": "curl https://api.anthropic.com/v1/messages \\\n  -H 'x-api-key: YOUR_API_KEY' \\\n  -H 'anthropic-version: 2023-06-01' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"model\": \"claude-3-5-sonnet-20241022\", \"max_tokens\": 1024, \"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}]}'",
                "js": "import Anthropic from '@anthropic-ai/sdk';\n\nconst client = new Anthropic({ apiKey: 'YOUR_API_KEY' });\nconst message = await client.messages.create({\n  model: 'claude-3-5-sonnet-20241022',\n  max_tokens: 1024,\n  messages: [{ role: 'user', content: 'Hello!' }],\n});\nconsole.log(message.content[0].text);"
            }
        },
        {
            "id": "gemini-1-5-pro", "name": "Gemini 1.5 Pro", "provider": "Google", "category": "chat",
            "badge": "Longest Context", "badge_color": "gradient-green",
            "description": "Google's most capable multimodal model with a 2M token context window for documents, code, images, audio, and video.",
            "tags": ["multimodal", "long-context", "vision", "audio"],
            "pricing": "$3.5 / 1M input tokens", "context": "2M tokens", "status": "GA",
            "docs_url": "https://ai.google.dev/gemini-api/docs/models/gemini",
            "snippet": {
                "python": "import google.generativeai as genai\n\ngenai.configure(api_key='YOUR_API_KEY')\nmodel = genai.GenerativeModel('gemini-1.5-pro')\n\nresponse = model.generate_content('Hello!')\nprint(response.text)",
                "curl": "curl 'https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-pro:generateContent?key=YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"contents\": [{\"parts\": [{\"text\": \"Hello!\"}]}]}'",
                "js": "import { GoogleGenerativeAI } from '@google/generative-ai';\n\nconst genAI = new GoogleGenerativeAI('YOUR_API_KEY');\nconst model = genAI.getGenerativeModel({ model: 'gemini-1.5-pro' });\nconst result = await model.generateContent('Hello!');\nconsole.log(result.response.text());"
            }
        },
        {
            "id": "llama-3-1-405b", "name": "Llama 3.1 405B", "provider": "Meta", "category": "chat",
            "badge": "Open Source", "badge_color": "gradient-orange",
            "description": "Meta's most powerful open-source model. Matches GPT-4 performance with full self-hosting capability and no data sharing.",
            "tags": ["open-source", "self-hostable", "reasoning", "multilingual"],
            "pricing": "Free (self-hosted)", "context": "128k tokens", "status": "GA",
            "docs_url": "https://llama.meta.com/docs/model-cards-and-prompt-formats/llama3_1/",
            "snippet": {
                "python": "from openai import OpenAI\n\nclient = OpenAI(\n    api_key='YOUR_API_KEY',\n    base_url='https://api.together.xyz/v1'\n)\nresponse = client.chat.completions.create(\n    model='meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo',\n    messages=[{'role': 'user', 'content': 'Hello!'}]\n)\nprint(response.choices[0].message.content)",
                "curl": "curl https://api.together.xyz/v1/chat/completions \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"model\": \"meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}]}'",
                "js": "import OpenAI from 'openai';\n\nconst client = new OpenAI({ apiKey: 'YOUR_API_KEY', baseURL: 'https://api.together.xyz/v1' });\nconst response = await client.chat.completions.create({\n  model: 'meta-llama/Meta-Llama-3.1-405B-Instruct-Turbo',\n  messages: [{ role: 'user', content: 'Hello!' }],\n});\nconsole.log(response.choices[0].message.content);"
            }
        },
        {
            "id": "mistral-large-2", "name": "Mistral Large 2", "provider": "Mistral AI", "category": "chat",
            "badge": "EU Sovereign", "badge_color": "gradient-pink",
            "description": "Mistral's flagship model with top-tier reasoning and coding. EU-hosted, GDPR-compliant, and cost-efficient.",
            "tags": ["reasoning", "coding", "multilingual", "gdpr-compliant"],
            "pricing": "$3 / 1M input tokens", "context": "128k tokens", "status": "GA",
            "docs_url": "https://docs.mistral.ai/getting-started/models/",
            "snippet": {
                "python": "from mistralai import Mistral\n\nclient = Mistral(api_key='YOUR_API_KEY')\nresponse = client.chat.complete(\n    model='mistral-large-latest',\n    messages=[{'role': 'user', 'content': 'Hello!'}]\n)\nprint(response.choices[0].message.content)",
                "curl": "curl https://api.mistral.ai/v1/chat/completions \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"model\": \"mistral-large-latest\", \"messages\": [{\"role\": \"user\", \"content\": \"Hello!\"}]}'",
                "js": "import MistralClient from '@mistralai/mistralai';\n\nconst client = new MistralClient('YOUR_API_KEY');\nconst response = await client.chat({\n  model: 'mistral-large-latest',\n  messages: [{ role: 'user', content: 'Hello!' }],\n});\nconsole.log(response.choices[0].message.content);"
            }
        },
    ],
    "image": [
        {
            "id": "dall-e-3", "name": "DALL-E 3", "provider": "OpenAI", "category": "image",
            "badge": "Best Prompt Following", "badge_color": "gradient-blue",
            "description": "OpenAI's most advanced image model with exceptional prompt adherence, detailed realism, and built-in content safety.",
            "tags": ["photorealistic", "illustration", "prompt-following", "safety"],
            "pricing": "$0.04 / image", "context": "4k prompt tokens", "status": "GA",
            "docs_url": "https://platform.openai.com/docs/guides/images",
            "snippet": {
                "python": "from openai import OpenAI\n\nclient = OpenAI(api_key='YOUR_API_KEY')\nresponse = client.images.generate(\n    model='dall-e-3',\n    prompt='A futuristic city at sunset, cyberpunk style',\n    size='1024x1024',\n    quality='standard',\n    n=1\n)\nprint(response.data[0].url)",
                "curl": "curl https://api.openai.com/v1/images/generations \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"model\": \"dall-e-3\", \"prompt\": \"A futuristic city at sunset\", \"n\": 1, \"size\": \"1024x1024\"}'",
                "js": "import OpenAI from 'openai';\n\nconst client = new OpenAI({ apiKey: 'YOUR_API_KEY' });\nconst image = await client.images.generate({\n  model: 'dall-e-3',\n  prompt: 'A futuristic city at sunset, cyberpunk style',\n  size: '1024x1024',\n});\nconsole.log(image.data[0].url);"
            }
        },
        {
            "id": "midjourney-v6", "name": "Midjourney v6", "provider": "Midjourney", "category": "image",
            "badge": "Best Aesthetics", "badge_color": "gradient-purple",
            "description": "The gold standard for artistic AI imagery. Unmatched aesthetic quality, style control, and photorealism.",
            "tags": ["artistic", "photorealistic", "style-control", "high-quality"],
            "pricing": "$10 / month (200 images)", "context": "—", "status": "GA",
            "docs_url": "https://docs.midjourney.com/",
            "snippet": {
                "python": "import requests\n\nresponse = requests.post(\n    'https://api.useapi.net/v2/jobs/imagine',\n    headers={'Authorization': 'Bearer YOUR_API_KEY'},\n    json={'prompt': 'A futuristic city at sunset --v 6 --ar 16:9'}\n)\nprint(response.json())",
                "curl": "curl https://api.useapi.net/v2/jobs/imagine \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"prompt\": \"A futuristic city at sunset --v 6 --ar 16:9\"}'",
                "js": "const response = await fetch('https://api.useapi.net/v2/jobs/imagine', {\n  method: 'POST',\n  headers: { 'Authorization': 'Bearer YOUR_API_KEY', 'Content-Type': 'application/json' },\n  body: JSON.stringify({ prompt: 'A futuristic city --v 6 --ar 16:9' }),\n});\nconsole.log(await response.json());"
            }
        },
        {
            "id": "stable-diffusion-xl", "name": "Stable Diffusion XL", "provider": "Stability AI", "category": "image",
            "badge": "Open Source", "badge_color": "gradient-green",
            "description": "Powerful open-source image generation with fine-tuning support, LoRA adapters, and self-hosting capability.",
            "tags": ["open-source", "fine-tunable", "self-hostable", "lora"],
            "pricing": "$0.002 / image", "context": "—", "status": "GA",
            "docs_url": "https://platform.stability.ai/docs/api-reference",
            "snippet": {
                "python": "import requests\n\nresponse = requests.post(\n    'https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image',\n    headers={'Authorization': 'Bearer YOUR_API_KEY'},\n    json={'text_prompts': [{'text': 'A futuristic city at sunset'}], 'cfg_scale': 7, 'steps': 30}\n)\nprint(response.json())",
                "curl": "curl https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"text_prompts\": [{\"text\": \"A futuristic city\"}], \"cfg_scale\": 7, \"steps\": 30}'",
                "js": "const response = await fetch(\n  'https://api.stability.ai/v1/generation/stable-diffusion-xl-1024-v1-0/text-to-image',\n  {\n    method: 'POST',\n    headers: { 'Authorization': 'Bearer YOUR_API_KEY', 'Content-Type': 'application/json' },\n    body: JSON.stringify({ text_prompts: [{ text: 'A futuristic city' }], steps: 30 }),\n  }\n);"
            }
        },
        {
            "id": "flux-pro", "name": "Flux Pro", "provider": "Black Forest Labs", "category": "image",
            "badge": "Fastest", "badge_color": "gradient-orange",
            "description": "Next-gen image model with exceptional text rendering, photorealism, and blazing-fast generation speed.",
            "tags": ["photorealistic", "text-rendering", "fast", "high-resolution"],
            "pricing": "$0.055 / image", "context": "—", "status": "GA",
            "docs_url": "https://docs.bfl.ml/",
            "snippet": {
                "python": "import requests\n\nresponse = requests.post(\n    'https://api.bfl.ml/v1/flux-pro',\n    headers={'x-key': 'YOUR_API_KEY'},\n    json={'prompt': 'A futuristic city at sunset', 'width': 1024, 'height': 1024}\n)\nprint(response.json())",
                "curl": "curl https://api.bfl.ml/v1/flux-pro \\\n  -H 'x-key: YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"prompt\": \"A futuristic city at sunset\", \"width\": 1024, \"height\": 1024}'",
                "js": "const response = await fetch('https://api.bfl.ml/v1/flux-pro', {\n  method: 'POST',\n  headers: { 'x-key': 'YOUR_API_KEY', 'Content-Type': 'application/json' },\n  body: JSON.stringify({ prompt: 'A futuristic city at sunset', width: 1024, height: 1024 }),\n});\nconsole.log(await response.json());"
            }
        },
        {
            "id": "ideogram-v2", "name": "Ideogram v2", "provider": "Ideogram", "category": "image",
            "badge": "Best Text in Images", "badge_color": "gradient-pink",
            "description": "Remarkable text legibility in generated images. Best-in-class for posters, logos, and typographic designs.",
            "tags": ["typography", "logo-design", "text-in-images", "poster"],
            "pricing": "$0.08 / image", "context": "—", "status": "GA",
            "docs_url": "https://developer.ideogram.ai/",
            "snippet": {
                "python": "import requests\n\nresponse = requests.post(\n    'https://api.ideogram.ai/generate',\n    headers={'Api-Key': 'YOUR_API_KEY'},\n    json={'image_request': {'prompt': 'Bold poster: FUTURE IS NOW', 'model': 'V_2'}}\n)\nprint(response.json())",
                "curl": "curl https://api.ideogram.ai/generate \\\n  -H 'Api-Key: YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"image_request\": {\"prompt\": \"Bold poster: FUTURE IS NOW\", \"model\": \"V_2\"}}'",
                "js": "const response = await fetch('https://api.ideogram.ai/generate', {\n  method: 'POST',\n  headers: { 'Api-Key': 'YOUR_API_KEY', 'Content-Type': 'application/json' },\n  body: JSON.stringify({ image_request: { prompt: 'Bold poster: FUTURE IS NOW', model: 'V_2' } }),\n});\nconsole.log(await response.json());"
            }
        },
    ],
    "video": [
        {
            "id": "sora", "name": "Sora", "provider": "OpenAI", "category": "video",
            "badge": "Most Realistic", "badge_color": "gradient-blue",
            "description": "OpenAI's groundbreaking text-to-video model. Generates cinematic, physically coherent videos up to 1 minute.",
            "tags": ["text-to-video", "cinematic", "physics", "long-duration"],
            "pricing": "Included in ChatGPT Pro", "context": "Up to 60s", "status": "GA",
            "docs_url": "https://sora.com/",
            "snippet": {
                "python": "from openai import OpenAI\n\nclient = OpenAI(api_key='YOUR_API_KEY')\n\n# Sora via API (preview)\nresponse = client.videos.generate(\n    model='sora',\n    prompt='A timelapse of a city street from day to night',\n    duration=10\n)\nprint(response.data[0].url)",
                "curl": "curl https://api.openai.com/v1/videos/generate \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"model\": \"sora\", \"prompt\": \"A timelapse of a city street from day to night\", \"duration\": 10}'",
                "js": "const response = await fetch('https://api.openai.com/v1/videos/generate', {\n  method: 'POST',\n  headers: { 'Authorization': 'Bearer YOUR_API_KEY', 'Content-Type': 'application/json' },\n  body: JSON.stringify({ model: 'sora', prompt: 'A timelapse of a city street', duration: 10 }),\n});"
            }
        },
        {
            "id": "runway-gen3", "name": "Runway Gen-3 Alpha", "provider": "Runway ML", "category": "video",
            "badge": "Best API Access", "badge_color": "gradient-purple",
            "description": "State-of-the-art text/image-to-video generation with precise motion control and cinematic quality.",
            "tags": ["text-to-video", "image-to-video", "motion-control", "api"],
            "pricing": "$0.05 / second", "context": "Up to 10s", "status": "GA",
            "docs_url": "https://docs.dev.runwayml.com/",
            "snippet": {
                "python": "import runwayml\n\nclient = runwayml.RunwayML(api_key='YOUR_API_KEY')\ntask = client.image_to_video.create(\n    model='gen3a_turbo',\n    prompt_image='https://example.com/image.jpg',\n    prompt_text='Camera slowly pans right',\n    duration=5\n)\nprint(task.id)",
                "curl": "curl https://api.dev.runwayml.com/v1/image_to_video \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'X-Runway-Version: 2024-11-06' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"model\": \"gen3a_turbo\", \"promptText\": \"Camera pans right\", \"duration\": 5}'",
                "js": "import RunwayML from '@runwayml/sdk';\n\nconst client = new RunwayML({ apiKey: 'YOUR_API_KEY' });\nconst task = await client.imageToVideo.create({\n  model: 'gen3a_turbo',\n  promptImage: 'https://example.com/image.jpg',\n  promptText: 'Camera slowly pans right',\n  duration: 5,\n});\nconsole.log(task.id);"
            }
        },
        {
            "id": "kling-ai", "name": "Kling AI 1.5", "provider": "Kuaishou", "category": "video",
            "badge": "Longest Duration", "badge_color": "gradient-green",
            "description": "Chinese video AI powerhouse with support for videos up to 3 minutes, complex motion, and professional quality.",
            "tags": ["long-duration", "text-to-video", "motion", "professional"],
            "pricing": "$0.14 / 5s clip", "context": "Up to 3 min", "status": "GA",
            "docs_url": "https://klingai.com/",
            "snippet": {
                "python": "import requests\n\nresponse = requests.post(\n    'https://api.klingai.com/v1/videos/text2video',\n    headers={'Authorization': 'Bearer YOUR_API_KEY'},\n    json={'prompt': 'A dragon flying over a medieval castle', 'duration': '5', 'mode': 'std'}\n)\nprint(response.json())",
                "curl": "curl https://api.klingai.com/v1/videos/text2video \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"prompt\": \"A dragon flying over a castle\", \"duration\": \"5\", \"mode\": \"std\"}'",
                "js": "const response = await fetch('https://api.klingai.com/v1/videos/text2video', {\n  method: 'POST',\n  headers: { 'Authorization': 'Bearer YOUR_API_KEY', 'Content-Type': 'application/json' },\n  body: JSON.stringify({ prompt: 'A dragon flying over a medieval castle', duration: '5', mode: 'std' }),\n});"
            }
        },
        {
            "id": "pika-labs", "name": "Pika 1.0", "provider": "Pika Labs", "category": "video",
            "badge": "Best Editing", "badge_color": "gradient-orange",
            "description": "AI video platform with powerful text-to-video, video editing, and modify-region capabilities.",
            "tags": ["text-to-video", "video-editing", "region-editing", "fast"],
            "pricing": "$8 / month", "context": "Up to 15s", "status": "GA",
            "docs_url": "https://pika.art/",
            "snippet": {
                "python": "import requests\n\nresponse = requests.post(\n    'https://api.pika.art/v1/generate',\n    headers={'Authorization': 'Bearer YOUR_API_KEY'},\n    json={'promptText': 'A sunset over the ocean with waves crashing', 'model': '1.5'}\n)\nprint(response.json())",
                "curl": "curl https://api.pika.art/v1/generate \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"promptText\": \"A sunset over the ocean\", \"model\": \"1.5\"}'",
                "js": "const response = await fetch('https://api.pika.art/v1/generate', {\n  method: 'POST',\n  headers: { Authorization: 'Bearer YOUR_API_KEY', 'Content-Type': 'application/json' },\n  body: JSON.stringify({ promptText: 'A sunset over the ocean with waves crashing', model: '1.5' }),\n});"
            }
        },
        {
            "id": "luma-dream-machine", "name": "Dream Machine", "provider": "Luma AI", "category": "video",
            "badge": "Smoothest Motion", "badge_color": "gradient-pink",
            "description": "Luma's flagship video model known for incredibly smooth motion, high fidelity, and consistent character rendering.",
            "tags": ["smooth-motion", "high-fidelity", "character-consistency", "api"],
            "pricing": "$0.0019 / second", "context": "Up to 10s", "status": "GA",
            "docs_url": "https://docs.lumalabs.ai/",
            "snippet": {
                "python": "import lumaai\n\nclient = lumaai.LumaAI(auth_token='YOUR_API_KEY')\ngeneration = client.generations.create(\n    prompt='A serene lake with mountains reflected in the water',\n    aspect_ratio='16:9'\n)\nprint(generation.id)",
                "curl": "curl https://api.lumalabs.ai/dream-machine/v1/generations \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"prompt\": \"A serene lake with mountains\", \"aspect_ratio\": \"16:9\"}'",
                "js": "import LumaAI from 'lumaai';\n\nconst client = new LumaAI({ authToken: 'YOUR_API_KEY' });\nconst generation = await client.generations.create({\n  prompt: 'A serene lake with mountains reflected in the water',\n  aspect_ratio: '16:9',\n});\nconsole.log(generation.id);"
            }
        },
    ],
    "audio": [
        {
            "id": "whisper-v3", "name": "Whisper v3", "provider": "OpenAI", "category": "audio",
            "badge": "Best Transcription", "badge_color": "gradient-blue",
            "description": "OpenAI's state-of-the-art speech recognition. 99 languages, near-human accuracy, and diarization support.",
            "tags": ["speech-to-text", "transcription", "multilingual", "open-source"],
            "pricing": "$0.006 / minute", "context": "25 MB audio", "status": "GA",
            "docs_url": "https://platform.openai.com/docs/guides/speech-to-text",
            "snippet": {
                "python": "from openai import OpenAI\n\nclient = OpenAI(api_key='YOUR_API_KEY')\n\nwith open('audio.mp3', 'rb') as f:\n    transcript = client.audio.transcriptions.create(\n        model='whisper-1', file=f, language='en'\n    )\nprint(transcript.text)",
                "curl": "curl https://api.openai.com/v1/audio/transcriptions \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -F model='whisper-1' \\\n  -F file='@audio.mp3'",
                "js": "import OpenAI from 'openai';\nimport fs from 'fs';\n\nconst client = new OpenAI({ apiKey: 'YOUR_API_KEY' });\nconst transcription = await client.audio.transcriptions.create({\n  model: 'whisper-1',\n  file: fs.createReadStream('audio.mp3'),\n});\nconsole.log(transcription.text);"
            }
        },
        {
            "id": "elevenlabs-v2", "name": "ElevenLabs Multilingual v2", "provider": "ElevenLabs", "category": "audio",
            "badge": "Most Natural TTS", "badge_color": "gradient-purple",
            "description": "The most natural-sounding TTS available. Voice cloning, 29 languages, emotional control, and real-time streaming.",
            "tags": ["text-to-speech", "voice-cloning", "emotional-control", "streaming"],
            "pricing": "$0.30 / 1k characters", "context": "—", "status": "GA",
            "docs_url": "https://elevenlabs.io/docs",
            "snippet": {
                "python": "from elevenlabs import ElevenLabs\n\nclient = ElevenLabs(api_key='YOUR_API_KEY')\naudio = client.generate(\n    text='Hello! This is ElevenLabs text-to-speech.',\n    voice='Rachel',\n    model='eleven_multilingual_v2'\n)\nwith open('output.mp3', 'wb') as f:\n    for chunk in audio:\n        f.write(chunk)",
                "curl": "curl https://api.elevenlabs.io/v1/text-to-speech/21m00Tcm4TlvDq8ikWAM \\\n  -H 'xi-api-key: YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"text\": \"Hello, this is ElevenLabs!\", \"model_id\": \"eleven_multilingual_v2\"}' \\\n  --output output.mp3",
                "js": "import ElevenLabs from 'elevenlabs';\n\nconst client = new ElevenLabs({ apiKey: 'YOUR_API_KEY' });\nconst audio = await client.generate({\n  text: 'Hello! This is ElevenLabs text-to-speech.',\n  voice: 'Rachel',\n  model_id: 'eleven_multilingual_v2',\n});"
            }
        },
        {
            "id": "suno-v4", "name": "Suno v4", "provider": "Suno", "category": "audio",
            "badge": "Best Music Gen", "badge_color": "gradient-green",
            "description": "Generate full studio-quality songs from text descriptions. Vocals, instruments, and mixing from a single prompt.",
            "tags": ["music-generation", "vocals", "full-songs", "text-to-music"],
            "pricing": "$8 / month (500 credits)", "context": "—", "status": "GA",
            "docs_url": "https://suno.com/",
            "snippet": {
                "python": "import requests\n\nresponse = requests.post(\n    'https://api.suno.ai/api/generate',\n    headers={'Authorization': 'Bearer YOUR_API_KEY'},\n    json={'prompt': 'An upbeat electronic dance track with synth leads', 'make_instrumental': False, 'wait_audio': True}\n)\nprint(response.json())",
                "curl": "curl https://api.suno.ai/api/generate \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"prompt\": \"An upbeat electronic dance track\", \"make_instrumental\": false}'",
                "js": "const response = await fetch('https://api.suno.ai/api/generate', {\n  method: 'POST',\n  headers: { Authorization: 'Bearer YOUR_API_KEY', 'Content-Type': 'application/json' },\n  body: JSON.stringify({ prompt: 'An upbeat electronic dance track with synth leads', make_instrumental: false }),\n});"
            }
        },
        {
            "id": "udio-v2", "name": "Udio v2", "provider": "Udio", "category": "audio",
            "badge": "Best Audio Quality", "badge_color": "gradient-orange",
            "description": "Udio's latest model produces extremely high-fidelity music with precise genre control and remixing capabilities.",
            "tags": ["music-generation", "high-fidelity", "genre-control", "remixing"],
            "pricing": "$10 / month", "context": "—", "status": "GA",
            "docs_url": "https://www.udio.com/",
            "snippet": {
                "python": "import requests\n\nresponse = requests.post(\n    'https://www.udio.com/api/generate-proxy',\n    headers={'Authorization': 'Bearer YOUR_API_KEY'},\n    json={'prompt': 'jazz fusion with electric guitar solo', 'samplerOptions': {'seed': -1}}\n)\nprint(response.json())",
                "curl": "curl https://www.udio.com/api/generate-proxy \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"prompt\": \"jazz fusion with electric guitar solo\"}'",
                "js": "const response = await fetch('https://www.udio.com/api/generate-proxy', {\n  method: 'POST',\n  headers: { Authorization: 'Bearer YOUR_API_KEY', 'Content-Type': 'application/json' },\n  body: JSON.stringify({ prompt: 'jazz fusion with electric guitar solo' }),\n});"
            }
        },
        {
            "id": "bark", "name": "Bark", "provider": "Suno AI", "category": "audio",
            "badge": "Open Source", "badge_color": "gradient-pink",
            "description": "Open-source text-to-audio model that generates speech with realistic emotion, music, and environmental sounds.",
            "tags": ["open-source", "text-to-audio", "emotional-speech", "sound-effects"],
            "pricing": "Free (self-hosted)", "context": "—", "status": "GA",
            "docs_url": "https://github.com/suno-ai/bark",
            "snippet": {
                "python": "from bark import SAMPLE_RATE, generate_audio, preload_models\nfrom scipy.io.wavfile import write as write_wav\n\npreload_models()\ntext_prompt = 'Hello, my name is Bark. [laughs] Pretty cool, right?'\naudio_array = generate_audio(text_prompt)\nwrite_wav('output.wav', SAMPLE_RATE, audio_array)",
                "curl": "# Bark runs locally — use via Replicate API\ncurl https://api.replicate.com/v1/predictions \\\n  -H 'Authorization: Bearer YOUR_REPLICATE_TOKEN' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"version\": \"b76242b40d67c76ab6742e987628a2a9ac019e11d56ab96c4e91ce03b79b2787\", \"input\": {\"prompt\": \"Hello from Bark! [laughs]\"}}'",
                "js": "const response = await fetch('https://api.replicate.com/v1/predictions', {\n  method: 'POST',\n  headers: { Authorization: 'Bearer YOUR_REPLICATE_TOKEN', 'Content-Type': 'application/json' },\n  body: JSON.stringify({ version: 'b76242b40d67c76ab6742e987628a2a9ac019e11d56ab96c4e91ce03b79b2787', input: { prompt: 'Hello from Bark! [laughs]' } }),\n});"
            }
        },
    ],
    "coding": [
        {
            "id": "github-copilot", "name": "GitHub Copilot", "provider": "GitHub / Microsoft", "category": "coding",
            "badge": "Most Adopted", "badge_color": "gradient-blue",
            "description": "The world's most widely used AI coding assistant. IDE integration, code completion, chat, and PR reviews.",
            "tags": ["code-completion", "ide-integration", "pr-review", "chat"],
            "pricing": "$10 / month", "context": "—", "status": "GA",
            "docs_url": "https://docs.github.com/en/copilot",
            "snippet": {
                "python": "import requests\n\nresponse = requests.post(\n    'https://models.inference.ai.azure.com/chat/completions',\n    headers={'Authorization': 'Bearer YOUR_GITHUB_TOKEN'},\n    json={'model': 'gpt-4o', 'messages': [{'role': 'user', 'content': 'Write a Python sort function'}]}\n)\nprint(response.json()['choices'][0]['message']['content'])",
                "curl": "curl https://models.inference.ai.azure.com/chat/completions \\\n  -H 'Authorization: Bearer YOUR_GITHUB_TOKEN' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"model\": \"gpt-4o\", \"messages\": [{\"role\": \"user\", \"content\": \"Write a Python sort function\"}]}'",
                "js": "import ModelClient from '@azure-rest/ai-inference';\nimport { AzureKeyCredential } from '@azure/core-auth';\n\nconst client = ModelClient('https://models.inference.ai.azure.com', new AzureKeyCredential(process.env.GITHUB_TOKEN));\nconst response = await client.path('/chat/completions').post({\n  body: { model: 'gpt-4o', messages: [{ role: 'user', content: 'Write a Python sort function' }] },\n});"
            }
        },
        {
            "id": "cursor-ai", "name": "Cursor AI", "provider": "Anysphere", "category": "coding",
            "badge": "Best IDE", "badge_color": "gradient-purple",
            "description": "AI-first code editor built on VS Code. Multi-file editing, codebase understanding, and natural language refactoring.",
            "tags": ["ai-editor", "multi-file", "codebase-aware", "refactoring"],
            "pricing": "$20 / month", "context": "Full codebase", "status": "GA",
            "docs_url": "https://docs.cursor.com/",
            "snippet": {
                "python": "import requests\n\nresponse = requests.post(\n    'https://api2.cursor.sh/aiserver.v1.AiService/StreamChat',\n    headers={'Authorization': 'Bearer YOUR_CURSOR_TOKEN'},\n    json={'conversation': [{'role': 'user', 'content': 'Refactor this function to use async/await'}]}\n)\nprint(response.text)",
                "curl": "curl https://api2.cursor.sh/aiserver.v1.AiService/StreamChat \\\n  -H 'Authorization: Bearer YOUR_CURSOR_TOKEN' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"conversation\": [{\"role\": \"user\", \"content\": \"Refactor this function\"}]}'",
                "js": "const response = await fetch('https://api2.cursor.sh/aiserver.v1.AiService/StreamChat', {\n  method: 'POST',\n  headers: { Authorization: 'Bearer YOUR_CURSOR_TOKEN', 'Content-Type': 'application/json' },\n  body: JSON.stringify({ conversation: [{ role: 'user', content: 'Refactor this function to use async/await' }] }),\n});"
            }
        },
        {
            "id": "devin", "name": "Devin 2.0", "provider": "Cognition AI", "category": "coding",
            "badge": "Autonomous Agent", "badge_color": "gradient-green",
            "description": "The world's first fully autonomous AI software engineer. Handles entire projects end-to-end with planning and execution.",
            "tags": ["autonomous-agent", "full-stack", "project-management", "debugging"],
            "pricing": "$500 / month", "context": "Full project", "status": "GA",
            "docs_url": "https://docs.cognition.ai/",
            "snippet": {
                "python": "import requests\n\nresponse = requests.post(\n    'https://api.cognition.ai/v1/sessions',\n    headers={'Authorization': 'Bearer YOUR_API_KEY'},\n    json={'prompt': 'Build a REST API for a todo app using FastAPI with SQLite', 'snapshot_id': 'default'}\n)\nsession = response.json()\nprint(f'Session URL: {session[\"url\"]}')",
                "curl": "curl https://api.cognition.ai/v1/sessions \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"prompt\": \"Build a REST API for a todo app using FastAPI\", \"snapshot_id\": \"default\"}'",
                "js": "const response = await fetch('https://api.cognition.ai/v1/sessions', {\n  method: 'POST',\n  headers: { Authorization: 'Bearer YOUR_API_KEY', 'Content-Type': 'application/json' },\n  body: JSON.stringify({ prompt: 'Build a REST API for a todo app using FastAPI', snapshot_id: 'default' }),\n});\nconsole.log('Session URL:', (await response.json()).url);"
            }
        },
        {
            "id": "claude-code", "name": "Claude Code", "provider": "Anthropic", "category": "coding",
            "badge": "Best Agentic", "badge_color": "gradient-orange",
            "description": "Anthropic's agentic coding tool. Understands entire codebases, writes and edits files, runs tests, and manages git.",
            "tags": ["agentic", "codebase-aware", "file-editing", "terminal-access"],
            "pricing": "$3-15 / 1M tokens", "context": "Full codebase", "status": "GA",
            "docs_url": "https://docs.anthropic.com/en/docs/claude-code",
            "snippet": {
                "python": "import anthropic\n\nclient = anthropic.Anthropic(api_key='YOUR_API_KEY')\nresponse = client.messages.create(\n    model='claude-opus-4-5',\n    max_tokens=4096,\n    messages=[{'role': 'user', 'content': 'Create a Flask REST API with user authentication'}]\n)\nprint(response.content[0].text)",
                "curl": "curl https://api.anthropic.com/v1/messages \\\n  -H 'x-api-key: YOUR_API_KEY' \\\n  -H 'anthropic-version: 2023-06-01' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"model\": \"claude-opus-4-5\", \"max_tokens\": 4096, \"messages\": [{\"role\": \"user\", \"content\": \"Create a Flask REST API\"}]}'",
                "js": "import Anthropic from '@anthropic-ai/sdk';\n\nconst client = new Anthropic({ apiKey: 'YOUR_API_KEY' });\nconst response = await client.messages.create({\n  model: 'claude-opus-4-5',\n  max_tokens: 4096,\n  messages: [{ role: 'user', content: 'Create a Flask REST API with user authentication' }],\n});\nconsole.log(response.content[0].text);"
            }
        },
        {
            "id": "replit-ai", "name": "Replit AI", "provider": "Replit", "category": "coding",
            "badge": "Best for Beginners", "badge_color": "gradient-pink",
            "description": "Cloud-native AI coding with instant deployment, debugging, and database integration — all in the browser.",
            "tags": ["cloud-ide", "instant-deploy", "beginner-friendly", "fullstack"],
            "pricing": "$25 / month", "context": "Project files", "status": "GA",
            "docs_url": "https://docs.replit.com/",
            "snippet": {
                "python": "import requests\n\nresponse = requests.post(\n    'https://production-modelfarm.replit.com/completion',\n    headers={'Authorization': 'Bearer YOUR_REPLIT_TOKEN'},\n    json={'model': 'replit-code-v1-3b', 'prompt': 'def fibonacci(n):', 'max_tokens': 200, 'temperature': 0.2}\n)\nprint(response.json()['completion'])",
                "curl": "curl https://production-modelfarm.replit.com/completion \\\n  -H 'Authorization: Bearer YOUR_REPLIT_TOKEN' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"model\": \"replit-code-v1-3b\", \"prompt\": \"def fibonacci(n):\", \"max_tokens\": 200}'",
                "js": "const response = await fetch('https://production-modelfarm.replit.com/completion', {\n  method: 'POST',\n  headers: { Authorization: 'Bearer YOUR_REPLIT_TOKEN', 'Content-Type': 'application/json' },\n  body: JSON.stringify({ model: 'replit-code-v1-3b', prompt: 'function fibonacci(n) {', max_tokens: 200 }),\n});"
            }
        },
    ],
    "embedding": [
        {
            "id": "text-embedding-3-large", "name": "text-embedding-3-large", "provider": "OpenAI", "category": "embedding",
            "badge": "Best Performance", "badge_color": "gradient-blue",
            "description": "OpenAI's highest-performing embedding model with 3072 dimensions, ideal for semantic search and RAG pipelines.",
            "tags": ["semantic-search", "rag", "high-dimensions", "multilingual"],
            "pricing": "$0.13 / 1M tokens", "context": "8191 tokens", "status": "GA",
            "docs_url": "https://platform.openai.com/docs/guides/embeddings",
            "snippet": {
                "python": "from openai import OpenAI\n\nclient = OpenAI(api_key='YOUR_API_KEY')\nresponse = client.embeddings.create(\n    model='text-embedding-3-large',\n    input='The quick brown fox jumps over the lazy dog'\n)\nembedding = response.data[0].embedding\nprint(f'Dimension: {len(embedding)}')",
                "curl": "curl https://api.openai.com/v1/embeddings \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"model\": \"text-embedding-3-large\", \"input\": \"The quick brown fox\"}'",
                "js": "import OpenAI from 'openai';\n\nconst client = new OpenAI({ apiKey: 'YOUR_API_KEY' });\nconst response = await client.embeddings.create({\n  model: 'text-embedding-3-large',\n  input: 'The quick brown fox jumps over the lazy dog',\n});\nconsole.log('Dimensions:', response.data[0].embedding.length);"
            }
        },
        {
            "id": "nomic-embed-text", "name": "nomic-embed-text", "provider": "Nomic AI", "category": "embedding",
            "badge": "Open Source", "badge_color": "gradient-purple",
            "description": "Fully open-source, auditable embedding model matching OpenAI ada-002 quality with 8192 token context window.",
            "tags": ["open-source", "auditable", "long-context", "self-hostable"],
            "pricing": "Free (self-hosted)", "context": "8192 tokens", "status": "GA",
            "docs_url": "https://docs.nomic.ai/reference/endpoints/nomic-embed-text",
            "snippet": {
                "python": "import requests\n\nresponse = requests.post(\n    'https://api-atlas.nomic.ai/v1/embedding/text',\n    headers={'Authorization': 'Bearer YOUR_NOMIC_KEY'},\n    json={'texts': ['Hello world'], 'model': 'nomic-embed-text-v1.5'}\n)\nprint(response.json())",
                "curl": "curl https://api-atlas.nomic.ai/v1/embedding/text \\\n  -H 'Authorization: Bearer YOUR_NOMIC_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"texts\": [\"Hello world\"], \"model\": \"nomic-embed-text-v1.5\"}'",
                "js": "const response = await fetch('https://api-atlas.nomic.ai/v1/embedding/text', {\n  method: 'POST',\n  headers: { 'Authorization': 'Bearer YOUR_NOMIC_KEY', 'Content-Type': 'application/json' },\n  body: JSON.stringify({ texts: ['Hello world'], model: 'nomic-embed-text-v1.5' }),\n});\nconsole.log(await response.json());"
            }
        },
        {
            "id": "cohere-embed-v3", "name": "Cohere Embed v3", "provider": "Cohere", "category": "embedding",
            "badge": "Best Multilingual", "badge_color": "gradient-green",
            "description": "Cohere's embedding model with 100+ language support, optimized separately for search and classification tasks.",
            "tags": ["multilingual", "100-languages", "semantic-search", "classification"],
            "pricing": "$0.10 / 1M tokens", "context": "512 tokens", "status": "GA",
            "docs_url": "https://docs.cohere.com/docs/cohere-embed",
            "snippet": {
                "python": "import cohere\n\nco = cohere.Client('YOUR_API_KEY')\nresponse = co.embed(\n    texts=['The quick brown fox', 'Hello world'],\n    model='embed-english-v3.0',\n    input_type='search_document'\n)\nprint(f'Embeddings: {len(response.embeddings)} x {len(response.embeddings[0])}')",
                "curl": "curl https://api.cohere.com/v1/embed \\\n  -H 'Authorization: Bearer YOUR_API_KEY' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"texts\": [\"Hello world\"], \"model\": \"embed-english-v3.0\", \"input_type\": \"search_document\"}'",
                "js": "import { CohereClient } from 'cohere-ai';\n\nconst cohere = new CohereClient({ token: 'YOUR_API_KEY' });\nconst response = await cohere.embed({\n  texts: ['The quick brown fox', 'Hello world'],\n  model: 'embed-english-v3.0',\n  inputType: 'search_document',\n});\nconsole.log('Count:', response.embeddings.length);"
            }
        },
        {
            "id": "bge-m3", "name": "BGE-M3", "provider": "BAAI", "category": "embedding",
            "badge": "Multi-Functionality", "badge_color": "gradient-orange",
            "description": "Multi-lingual, multi-granularity embedding model supporting dense, sparse, and multi-vector retrieval strategies.",
            "tags": ["multilingual", "multi-vector", "sparse-retrieval", "open-source"],
            "pricing": "Free (self-hosted)", "context": "8192 tokens", "status": "GA",
            "docs_url": "https://huggingface.co/BAAI/bge-m3",
            "snippet": {
                "python": "from FlagEmbedding import BGEM3FlagModel\n\nmodel = BGEM3FlagModel('BAAI/bge-m3', use_fp16=True)\nsentences = ['The quick brown fox', 'Hello world']\nembeddings = model.encode(\n    sentences, batch_size=12, max_length=8192,\n    return_dense=True, return_sparse=True\n)\nprint(f'Dense shape: {embeddings[\"dense_vecs\"].shape}')",
                "curl": "curl https://api-inference.huggingface.co/pipeline/feature-extraction/BAAI/bge-m3 \\\n  -H 'Authorization: Bearer YOUR_HF_TOKEN' \\\n  -H 'Content-Type: application/json' \\\n  -d '{\"inputs\": [\"The quick brown fox\", \"Hello world\"]}'",
                "js": "const response = await fetch(\n  'https://api-inference.huggingface.co/pipeline/feature-extraction/BAAI/bge-m3',\n  {\n    method: 'POST',\n    headers: { Authorization: 'Bearer YOUR_HF_TOKEN', 'Content-Type': 'application/json' },\n    body: JSON.stringify({ inputs: ['The quick brown fox', 'Hello world'] }),\n  }\n);"
            }
        },
    ],
}

# ---------------------------------------------------------------------------
# PRICING PLANS — AI Pricing
# ---------------------------------------------------------------------------
PLANS = [
    {"key": "free", "name": "Free", "tagline": "Explore the playground", "price": "0", "period": "/month",
     "gradient": "linear-gradient(135deg, #2B86C5, #00D4FF)", "cta": "Get Started", "popular": False,
     "features": ["5 Chat models access", "100 API requests / day", "1 Image model (DALL-E 3)", "Community support", "API key management", "Basic usage analytics"]},
    {"key": "starter", "name": "Starter", "tagline": "Power up your workflow", "price": "19", "period": "/month",
     "gradient": "linear-gradient(135deg, #784BA0, #C850C0)", "cta": "Start Free Trial", "popular": False,
     "features": ["All Chat models", "1,000 requests / day", "All Image models", "2 Video models", "Email support", "Usage analytics dashboard", "Webhook integrations"]},
    {"key": "pro", "name": "Pro", "tagline": "The full AI arsenal", "price": "79", "period": "/month",
     "gradient": "linear-gradient(135deg, #FF3CAC, #784BA0, #2B86C5)", "cta": "Go Pro", "popular": True,
     "features": ["All 30+ models", "Unlimited requests", "All Video + Audio models", "All Coding Agents", "All Embedding models", "Priority support", "Team collaboration (5 seats)", "Advanced analytics", "Custom integrations"]},
    {"key": "enterprise", "name": "Enterprise", "tagline": "Scale without limits", "price": "Custom", "period": "",
     "gradient": "linear-gradient(135deg, #E17055, #FDCB6E)", "cta": "Contact Sales", "popular": False,
     "features": ["Everything in Pro", "Unlimited seats", "Custom model fine-tuning", "SLA guarantee (99.9%)", "Dedicated infrastructure", "On-premise deployment", "24/7 enterprise support", "SSO + SAML", "Custom contracts"]},
]

# ---------------------------------------------------------------------------
# METADATA
# ---------------------------------------------------------------------------
CAT_LABELS = {"chat": "Chat Models", "image": "Image Models", "video": "Video Models",
               "audio": "Audio Models", "coding": "Coding Agents", "embedding": "Embedding Models"}
CAT_ICONS  = {"chat": "💬", "image": "🎨", "video": "🎬", "audio": "🎵", "coding": "⚡", "embedding": "🔢"}
CAT_DESCRIPTIONS = {
    "chat":      "Conversational AI with advanced reasoning and multimodal capabilities",
    "image":     "Text-to-image generation with photorealism and artistic control",
    "video":     "Text and image-to-video generation with cinematic quality",
    "audio":     "Speech recognition, text-to-speech, and AI music generation",
    "coding":    "AI-powered coding assistants and autonomous software agents",
    "embedding": "High-dimensional vector representations for semantic search and RAG",
}


def _build_index():
    """Build flat model index once at startup — O(1) lookups thereafter."""
    return {m["id"]: m for lst in MODELS.values() for m in lst}


MODEL_INDEX = _build_index()

# ---------------------------------------------------------------------------
# ROUTES
# ---------------------------------------------------------------------------
@app.route("/")
def index():
    return render_template("index.html", models=MODELS, cat_labels=CAT_LABELS,
                           cat_icons=CAT_ICONS, cat_descriptions=CAT_DESCRIPTIONS)

@app.route("/chat")
def chat():
    return render_template("chat.html", models=MODELS["chat"], category="chat",
        label=CAT_LABELS["chat"], icon=CAT_ICONS["chat"], description=CAT_DESCRIPTIONS["chat"])

@app.route("/image")
def image():
    return render_template("image.html", models=MODELS["image"], category="image",
        label=CAT_LABELS["image"], icon=CAT_ICONS["image"], description=CAT_DESCRIPTIONS["image"])

@app.route("/video")
def video():
    return render_template("video.html", models=MODELS["video"], category="video",
        label=CAT_LABELS["video"], icon=CAT_ICONS["video"], description=CAT_DESCRIPTIONS["video"])

@app.route("/audio")
def audio():
    return render_template("audio.html", models=MODELS["audio"], category="audio",
        label=CAT_LABELS["audio"], icon=CAT_ICONS["audio"], description=CAT_DESCRIPTIONS["audio"])

@app.route("/coding")
def coding():
    return render_template("coding.html", models=MODELS["coding"], category="coding",
        label=CAT_LABELS["coding"], icon=CAT_ICONS["coding"], description=CAT_DESCRIPTIONS["coding"])

@app.route("/embedding")
def embedding():
    return render_template("embedding.html", models=MODELS["embedding"], category="embedding",
        label=CAT_LABELS["embedding"], icon=CAT_ICONS["embedding"], description=CAT_DESCRIPTIONS["embedding"])

@app.route("/pricing")
def pricing():
    return render_template("pricing.html", plans=PLANS)


# ---------------------------------------------------------------------------
# API
# ---------------------------------------------------------------------------
@app.route("/api/search")
def api_search():
    q   = request.args.get("q", "").lower().strip()
    cat = request.args.get("cat", "all")
    if len(q) < 2:
        return jsonify({"results": []})
    pool = MODELS.get(cat, []) if cat != "all" else [m for lst in MODELS.values() for m in lst]
    results = []
    for model in pool:
        searchable = (model["name"] + " " + model["provider"] + " " +
                      " ".join(model["tags"]) + " " + model["description"]).lower()
        if q in searchable:
            results.append({"id": model["id"], "name": model["name"], "category": model["category"],
                            "provider": model["provider"], "badge": model.get("badge", ""),
                            "url": f"/{model['category']}#{model['id']}"})
    return jsonify({"results": results[:20]})


@app.route("/api/integrate/<model_id>")
def api_integrate(model_id):
    model = MODEL_INDEX.get(model_id)   # O(1)
    if not model:
        return jsonify({"error": "Model not found"}), 404
    return jsonify({"name": model["name"], "snippet": model["snippet"], "docs": model["docs_url"]})


# ---------------------------------------------------------------------------
# ASK  — Primary: Groq (free, 14 400 req/day, 30 req/min, ultra-fast)
#        Fallback: Wikipedia
# Get a free key at: https://console.groq.com  (no credit card needed)
# Add to .env:  GROQ_API_KEY=your_key_here
# ---------------------------------------------------------------------------
_GROQ_KEY  = os.environ.get("GROQ_API_KEY", "")
_GROQ_URL  = "https://api.groq.com/openai/v1/chat/completions"
# Tried in order — each has its own rate-limit bucket
_GROQ_MODELS = [
    "llama-3.3-70b-versatile",   # best quality, free
    "llama3-8b-8192",            # faster, lighter
    "gemma2-9b-it",              # Google Gemma via Groq
]

_FOLLOWUP = re.compile(
    r'^\s*(tell me more|more|elaborate|go on|continue|details?|explain more'
    r'|what about|and also|how about)\b'
    r'|\b(it|that|this|they|them|its|their)\b',
    re.IGNORECASE,
)

_JSON_FENCE  = re.compile(r'```(?:json)?\s*([\s\S]*?)```', re.IGNORECASE)
_HTML_TAGS   = re.compile(r'<[^>]+>')
_DISAMBIG    = re.compile(r'may refer to|can refer to|following may|disambiguation', re.I)
_WIKI_API    = "https://en.wikipedia.org/w/api.php"
_WIKI_HEADERS= {"User-Agent": "ModelHub/1.0 (local dev)"}


# ── Groq ──────────────────────────────────────────────────────
def _extract_json(raw: str) -> dict:
    """Robustly pull a JSON object out of LLM response text."""
    fence_match = _JSON_FENCE.search(raw)
    candidate = fence_match.group(1).strip() if fence_match else raw
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        pass
    start = raw.find('{')
    end   = raw.rfind('}')
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(raw[start:end + 1])
        except json.JSONDecodeError:
            pass
    raise ValueError(f"No valid JSON in response: {raw[:200]}")


def _ask_groq(question: str, context_topic: str = "") -> tuple:
    """Returns (parsed_dict, model_name). Tries each model until one succeeds."""
    context_line = (
        f'This is a follow-up about "{context_topic}". '
        if context_topic else ""
    )
    system_msg = (
        "You are a concise AI summarizer. Always respond with ONLY a JSON object "
        "(no markdown, no extra text) in exactly this format:\n"
        '{"title":"Short topic title","description":"One sentence overview.",'
        '"bullets":["Point one.","Point two.","Point three.","Point four.","Point five."]}\n'
        "Rules: 4-6 bullets max. Each bullet is one complete sentence ending with a period. "
        "Be factual and educational."
    )
    user_msg = f"{context_line}{question}"

    last_exc = None
    for model in _GROQ_MODELS:
        try:
            resp = _HTTP.post(
                _GROQ_URL,
                headers={"Authorization": f"Bearer {_GROQ_KEY}",
                         "Content-Type": "application/json"},
                json={
                    "model": model,
                    "messages": [
                        {"role": "system", "content": system_msg},
                        {"role": "user",   "content": user_msg},
                    ],
                    "temperature": 0.3,
                    "max_tokens": 600,
                },
                timeout=20,
            )
            resp.raise_for_status()
            raw = resp.json()["choices"][0]["message"]["content"].strip()
            return _extract_json(raw), model
        except http_requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if status in (429, 503):
                print(f"[Groq] {model} skipped ({status}), trying next…")
                last_exc = exc
                continue
            raise
        except Exception as exc:
            print(f"[Groq] {model} error: {type(exc).__name__}: {exc}")
            last_exc = exc
            continue
    raise last_exc or RuntimeError("All Groq models failed")


# ── Wikipedia fallback ────────────────────────────────────────
def _to_bullets(text, n=6):
    raw = re.split(r'(?<=[.!?])\s+|\n{2,}', text.strip())
    for threshold in (30, 15):
        bullets = []
        for s in raw:
            s = s.strip()
            if not s or len(s) < threshold:
                continue
            if s.startswith('==') or s.isupper() or _DISAMBIG.search(s):
                continue
            if s[-1] not in '.!?':
                s += '.'
            bullets.append(s)
            if len(bullets) >= n:
                break
        if len(bullets) >= 2:
            break
    return bullets


def _fetch_wiki(topic: str) -> dict:
    """Search Wikipedia and return {title, description, bullets, url}."""
    s = _HTTP.get(_WIKI_API,
        params={"action": "query", "list": "search", "srsearch": topic,
                "format": "json", "srlimit": 5, "utf8": 1},
        headers=_WIKI_HEADERS, timeout=8)
    s.raise_for_status()
    hits = s.json().get("query", {}).get("search", [])
    if not hits:
        return {}

    for hit in hits:
        candidate = hit["title"]
        if "(disambiguation)" in candidate.lower():
            continue
        for full in (False, True):
            params = {"action": "query", "prop": "extracts", "explaintext": 1,
                      "titles": candidate, "format": "json", "redirects": 1, "utf8": 1}
            if full:
                params["exsentences"] = 12
            else:
                params["exintro"] = 1
            r = _HTTP.get(_WIKI_API, params=params, headers=_WIKI_HEADERS, timeout=8)
            r.raise_for_status()
            pages   = r.json().get("query", {}).get("pages", {})
            extract = (next(iter(pages.values()), {}).get("extract") or "").strip()
            if extract and not _DISAMBIG.search(extract) and len(extract) >= 60:
                break
        else:
            continue

        bullets = _to_bullets(extract, n=6)
        if not bullets:
            lines   = [l.strip() for l in extract.splitlines() if len(l.strip()) > 20]
            bullets = [l if l[-1] in '.!?' else l + '.' for l in lines[:6]]
        if not bullets:
            continue

        wiki_url = f"https://en.wikipedia.org/wiki/{candidate.replace(' ', '_')}"
        desc     = _HTML_TAGS.sub("", hit.get("snippet", "")).strip()
        return {"title": candidate, "description": desc,
                "bullets": bullets, "url": wiki_url,
                "source": f"Wikipedia — {candidate}"}
    return {}


@app.route("/api/ask")
def api_ask():
    """
    Answer any question. Primary: Gemini 2.0 Flash. Fallback: Wikipedia.
    Supports context_topic for multi-turn follow-up awareness.
    """
    q             = request.args.get("q", "").strip()
    context_topic = request.args.get("context_topic", "").strip()

    if len(q) < 2:
        return jsonify({"error": "Query too short."}), 400

    is_followup    = bool(context_topic and (len(q.split()) <= 3 or _FOLLOWUP.search(q)))
    resolved_topic = context_topic if is_followup else q

    # ── Try Groq first ───────────────────────────────────────
    if _GROQ_KEY:
        try:
            data, used_model = _ask_groq(q, context_topic=context_topic if is_followup else "")
            bullets = data.get("bullets") or []
            if bullets:
                model_label = used_model.replace("-", " ").title()
                return jsonify({
                    "query":       q,
                    "topic":       resolved_topic,
                    "title":       data.get("title", q.title()),
                    "description": data.get("description", ""),
                    "bullets":     bullets,
                    "source":      f"Groq — {model_label}",
                    "url":         "",
                })
        except http_requests.HTTPError as exc:
            status = exc.response.status_code if exc.response is not None else 0
            if status == 401:
                return jsonify({"error": "Invalid Groq API key. Check GROQ_API_KEY in your .env file."}), 503
            print(f"[Groq HTTP {status}] falling back to Wikipedia")
            # any other error → fall through to Wikipedia
        except Exception as exc:
            print(f"[Groq error] {type(exc).__name__}: {exc}")
            # fall through to Wikipedia

    # ── Wikipedia fallback ────────────────────────────────────
    topic = resolved_topic if is_followup else re.sub(
        r'^(what is|what are|who is|how does|explain|define|tell me about)\s+',
        '', q, flags=re.IGNORECASE).strip() or q
    try:
        wiki = _fetch_wiki(topic)
    except Exception as exc:
        return jsonify({"error": f"Both Groq and Wikipedia unavailable ({type(exc).__name__})."}), 502

    if not wiki:
        return jsonify({"error": f'No results found for "{topic}". Try rephrasing.'}), 404

    return jsonify({
        "query":       q,
        "topic":       resolved_topic,
        "title":       wiki["title"],
        "description": wiki["description"],
        "bullets":     wiki["bullets"],
        "source":      wiki["source"],
        "url":         wiki["url"],
    })


if __name__ == "__main__":
    app.run(debug=True)
