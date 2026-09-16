import ollama

response = ollama.chat(
	model="llama3.1:8b",
	messages=[
	 {
		"role":"user",
		"content":"Say hello to yourself."
	 }
	]
)

print(response["message"]["content"])