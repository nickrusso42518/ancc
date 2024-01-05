from openai import OpenAI
client = OpenAI()

completion = client.chat.completions.create(
  model="gpt-3.5-turbo",
  messages=[
    {"role": "system", "content": "You are a senior network engineer with extensive experience with Cisco products."},
    {"role": "user", "content": "In 4 sentences or less, summarize the difference between Cisco IOS-XE and Cisco IOS-XR"}
  ]
)

print(completion.choices[0].message)
