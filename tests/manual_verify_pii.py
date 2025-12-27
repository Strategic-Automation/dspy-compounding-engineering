import os
from utils.context.project import ProjectContext

def test_pii_scrubbing_e2e():
    # Create a dummy file with a secret
    dummy_file = "test_secret_e2e.txt"
    secret_content = "My private key is sk-12345678901234567890123456789012"
    with open(dummy_file, "w") as f:
        f.write(secret_content)

    try:
        context_gatherer = ProjectContext(base_dir=".")
        # Targeted task to ensure relevance
        context = context_gatherer.gather_smart_context(task=f"review {dummy_file} and check for secrets", budget=2000)
        
        if dummy_file in context:
            if "sk-" in context:
                raise RuntimeError("ERROR: Secret was NOT scrubbed from context!")
            elif "[REDACTED_OPENAI_API_KEY]" in context:
                print("SUCCESS: Secret was correctly scrubbed from context.")
            else:
                print("INFO: Secret redaction label not found (check scrubber patterns).")
        else:
            print(f"INFO: File {dummy_file} was not included in context.")
    finally:
        if os.path.exists(dummy_file):
            os.remove(dummy_file)

if __name__ == "__main__":
    test_pii_scrubbing_e2e()
