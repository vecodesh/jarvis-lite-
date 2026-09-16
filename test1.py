import ollama

response = ollama.chat(
	model = "llama3.1:8b",
	messages=[
	{
		"role" : "user",
		"content" : "Would you please propose me"
	}
	]
)

print(response["message"])