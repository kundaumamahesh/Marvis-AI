import json
import requests
import asyncio
import re
import os

from memory.memory_manager import MemoryManager


class LLMClient:

    def __init__(self):

        self.api_key = os.getenv("OPENROUTER_API_KEY")

        self.url = (
            "https://openrouter.ai/api/v1/chat/completions"
        )

        self.model = (
            "openrouter/owl-alpha"
        )

        self.memory = MemoryManager()

    # ----------------------------------
    # ROUTER JSON DETECTION
    # ----------------------------------
    def is_router_json(self, text):
        """
        Detects if the model accidentally returned routing JSON
        instead of a natural response.
        """

        try:
            match = re.search(r"\{.*\}", text, re.DOTALL)

            if not match:
                return False

            data = json.loads(match.group())

            return (
                isinstance(data, dict)
                and "task" in data
                and "confidence" in data
            )

        except:
            return False

    # ----------------------------------
    # STANDARD GENERATION
    # ----------------------------------
    async def generate(
        self,
        system_prompt,
        user_prompt,
        use_history=True,
        save_to_memory=True
    ):

        try:

            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                }
            ]

            if use_history:
                history = self.memory.get()
                messages.extend(history)

            messages.append({
                "role": "user",
                "content": user_prompt
            })

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7
            }

            headers = {
                "Authorization":
                f"Bearer {self.api_key}",
                "Content-Type":
                "application/json"
            }

            response = requests.post(
                self.url,
                json=payload,
                headers=headers,
                timeout=120
            )

            response.raise_for_status()

            data = response.json()

            print("\n[LLM RAW RESPONSE]")
            print(json.dumps(data, indent=2))

            reply = (
                data
                .get("choices", [{}])[0]
                .get("message", {})
                .get("content", "")
            )

            if not reply:
                return "Sorry, I couldn't generate a response."

            reply = reply.strip()

            # ==================================================
            # FIX FOR OWL-ALPHA RETURNING ROUTER JSON
            # ==================================================
            if save_to_memory and self.is_router_json(reply):

                lower = user_prompt.lower().strip()

                greetings = [
                    "hi",
                    "hello",
                    "hey",
                    "yo",
                    "good morning",
                    "good evening"
                ]

                if lower in greetings:
                    reply = (
                        "Hey! 😊 I'm here and ready to help. "
                        "What would you like to do?"
                    )

                else:
                    retry_messages = [
                        {
                            "role": "system",
                            "content":
                            (
                                "You are MARVIS, a helpful AI assistant. "
                                "DO NOT output JSON. "
                                "DO NOT output routing objects. "
                                "Reply naturally like ChatGPT."
                            )
                        },
                        {
                            "role": "user",
                            "content": user_prompt
                        }
                    ]

                    retry_payload = {
                        "model": self.model,
                        "messages": retry_messages,
                        "temperature": 0.7
                    }

                    retry_response = requests.post(
                        self.url,
                        json=retry_payload,
                        headers=headers,
                        timeout=120
                    )

                    retry_data = retry_response.json()

                    retry_reply = (
                        retry_data
                        .get("choices", [{}])[0]
                        .get("message", {})
                        .get("content", "")
                    )

                    if retry_reply:
                        reply = retry_reply.strip()

            if save_to_memory:
                self.memory.add(
                    "user",
                    user_prompt
                )

                self.memory.add(
                    "assistant",
                    reply
                )

            return reply

        except Exception as e:

            print("[LLM ERROR]", str(e))

            return (
                f"LLM Error: {str(e)}"
            )

    # ----------------------------------
    # STREAM GENERATION
    # ----------------------------------
    async def generate_stream(
        self,
        system_prompt,
        user_prompt,
        use_history=True,
        save_to_memory=True
    ):

        try:

            response = await self.generate(
                system_prompt,
                user_prompt,
                use_history=use_history,
                save_to_memory=save_to_memory
            )

            words = response.split()

            for word in words:

                yield word + " "

                await asyncio.sleep(
                    0.02
                )

        except Exception as e:

            yield (
                f"Streaming Error: "
                f"{str(e)}"
            )