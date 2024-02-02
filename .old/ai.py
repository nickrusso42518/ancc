from openai import OpenAI

client = OpenAI()
completion = client.chat.completions.create(
    model="gpt-3.5-turbo",
    messages=[
        {
            "role": "system",
            "content": "You are a senior network engineer with extensive experience with Cisco products.",
        },
        {
            "role": "user",
            "content": "In 4 sentences or less, summarize the difference between Cisco IOS-XE and Cisco IOS-XR",
        },
    ],
)

print(completion.choices[0].message)
###
context = "You are chatting with a customer service representative."
message = "Hi, I have a problem with my account."
response = openai.Completion.create(
    engine="gpt-3.5-turbo",
    prompt=f"Chat:\n{context}\nUser: {message}\n",
    max_tokens=50,
)

reply = response.choices[0].text.strip()
print(reply)
"""
client = OpenAI()

response = client.chat.completions.create(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "system", "content": "You are a helpful assistant."},
    {"role": "user", "content": "Who won the world series in 2020?"},
    {"role": "assistant", "content": "The Los Angeles Dodgers won the World Series in 2020."},
    {"role": "user", "content": "Where was it played?"}
  ]
)
"""
