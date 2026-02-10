from groq import Groq
import traceback

with open("output.txt", "w") as f:
    try:
        client = Groq(api_key="your_api_key_here")
        
        f.write("--- Testing llama-3.1-8b-instant ---\n")
        try:
            completion = client.chat.completions.create(
                model="llama-3.1-8b-instant",
                messages=[{"role": "user", "content": "Hi"}],
            )
            f.write(f"Success: {completion.choices[0].message.content}\n")
        except Exception as e:
            f.write(f"Failed: {e}\n")

        f.write("\n--- Available Models ---\n")
        models = client.models.list()
        for model in models.data:
            f.write(f"Model ID: {model.id}\n")
            
    except Exception:
        traceback.print_exc(file=f)
