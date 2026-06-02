import json
import requests
import asyncio
import re
import os
import threading

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
        self.vector_memory = None
        self.memory_active = False

        # Asynchronously load Vector Memory in the background so app starts instantly
        threading.Thread(target=self._init_vector_memory, daemon=True).start()

    def _init_vector_memory(self):
        try:
            from memory.vector_memory import VectorMemory
            self.vector_memory = VectorMemory()
            self.memory_active = True
            print("[System] Semantic Vector Memory initialized successfully.")
        except Exception as e:
            print(f"[System INFO] Semantic Vector Memory inactive: {e}")

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
                # ── SEMANTIC VECTOR RAG ────────────────────────────────────
                if self.memory_active and self.vector_memory:
                    try:
                        past_memories = self.vector_memory.search(user_prompt)
                        if past_memories:
                            context_str = "\n".join([f"- {m}" for m in past_memories if m.strip()])
                            if context_str:
                                system_prompt += f"\n\n[RELEVANT PAST CONTEXTS]\n{context_str}"
                                messages[0]["content"] = system_prompt
                    except Exception:
                        pass

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

                if self.memory_active and self.vector_memory:
                    try:
                        self.vector_memory.add_memory(f"User: {user_prompt} | Assistant: {reply}")
                    except Exception:
                        pass

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
            messages = [
                {
                    "role": "system",
                    "content": system_prompt
                }
            ]

            if use_history:
                # ── SEMANTIC VECTOR RAG ────────────────────────────────────
                if self.memory_active and self.vector_memory:
                    try:
                        past_memories = self.vector_memory.search(user_prompt)
                        if past_memories:
                            context_str = "\n".join([f"- {m}" for m in past_memories if m.strip()])
                            if context_str:
                                system_prompt += f"\n\n[RELEVANT PAST CONTEXTS]\n{context_str}"
                                messages[0]["content"] = system_prompt
                    except Exception:
                        pass

                history = self.memory.get()
                messages.extend(history)

            messages.append({
                "role": "user",
                "content": user_prompt
            })

            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": 0.7,
                "stream": True
            }

            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }

            def perform_request():
                return requests.post(
                    self.url,
                    json=payload,
                    headers=headers,
                    timeout=120,
                    stream=True
                )

            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(None, perform_request)
            response.raise_for_status()

            full_reply = ""
            for line in response.iter_lines():
                if line:
                    decoded_line = line.decode('utf-8').strip()
                    if decoded_line.startswith("data: "):
                        data_str = decoded_line[6:]
                        if data_str == "[DONE]":
                            break
                        try:
                            chunk_data = json.loads(data_str)
                            token = chunk_data.get("choices", [{}])[0].get("delta", {}).get("content", "")
                            if token:
                                full_reply += token
                                yield token
                        except Exception:
                            pass
                await asyncio.sleep(0.001)

            if save_to_memory and full_reply:
                # Deduplicate or clean greeting intercepts in streaming if necessary
                self.memory.add("user", user_prompt)
                self.memory.add("assistant", full_reply.strip())

                if self.memory_active and self.vector_memory:
                    try:
                        self.vector_memory.add_memory(f"User: {user_prompt} | Assistant: {full_reply.strip()}")
                    except Exception:
                        pass

        except Exception as e:
            print("[LLM STREAM ERROR]", str(e))
            yield f"Streaming Error: {str(e)}"