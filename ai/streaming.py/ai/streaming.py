import httpx
        self.api_key = os.getenv(
            "OPENROUTER_API_KEY"
        )

    async def stream(
        self,
        system,
        prompt,
        callback
    ):

        async with httpx.AsyncClient(
            timeout=None
        ) as client:

            async with client.stream(
                "POST",
                "https://openrouter.ai/api/v1/chat/completions",

                headers={
                    "Authorization": (
                        f"Bearer {self.api_key}"
                    ),
                    "Content-Type": "application/json"
                },

                json={
                    "model": "openai/gpt-4o-mini",
                    "messages": [
                        {
                            "role": "system",
                            "content": system
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    "stream": True
                }
            ) as response:

                async for line in response.aiter_lines():

                    if line.startswith("data: "):

                        line = line[6:]

                        if line == "[DONE]":
                            break

                        try:

                            data = json.loads(line)

                            delta = (
                                data["choices"][0]
                                ["delta"]
                                .get("content", "")
                            )

                            if delta:
                                callback(delta)

                        except:
                            pass
