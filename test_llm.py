from llm_client import HuggingFaceLLMClient

def main():
    llm = HuggingFaceLLMClient("google/gemma-2-2b-it")
    prompt = 'Return ONLY valid JSON. Output exactly: {"hello":"world"}'
    out = llm.generate(prompt, max_new_tokens=200, temperature=0.0)

    print(" RAW OUTPUT START ")
    print(repr(out))
    print(out)
    print(" RAW OUTPUT END ")

if __name__ == "__main__":
    main()
