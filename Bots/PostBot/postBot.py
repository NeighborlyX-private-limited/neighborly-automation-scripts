import os, sys, json, random, requests
from dotenv import load_dotenv
from constants import botLocationInfo, templates
from openai import OpenAI
from google import genai
from google.genai import types

class PostBot:
    def __init__(self):
        load_dotenv(dotenv_path="./config.env")
        self.GeminiAI_api_key = os.getenv("GEMINI_API_KEY")
        self.OpenAI_api_key = os.getenv("OPENAI_API_KEY")
        self.locationInfo = None
        self.GeminiAIclient = None
        self.OpenAIclient = None
        self.accessToken = None
        self.refreshToken = None
        self.postCreated = 0
        self.unsuccessfulAttempts = 0

    # Login with environment saved credentials to interact with the Backend API.
    def login(self):
        try:
            emails = os.getenv("EMAILS").split("|")
            passwords = os.getenv("PASSWORDS").split("|")

            emailsLength = len(emails)
            passwordsLength = len(passwords)

            if emailsLength <= 0 or emailsLength != passwordsLength:
                raise Exception("Invalid email or password list.Fix Environment variables.")

            idx = random.randint(0, emailsLength - 1)
            botUserId, botPassword = emails[idx], passwords[idx]

            url = os.getenv("BASE_URL") + os.getenv("LOGIN_ENDPOINT")
            headers = {
                "Content-Type": "application/json",
            }
            payload = {
                "userId": botUserId,
                "password": botPassword,
            }
            # Make API call to login and get tokens.
            response = requests.post(url, headers=headers, json=payload)

            if response.status_code == 200:
                result = response.json()
                self.accessToken = result.get("accessToken")
                self.refreshToken = result.get("refreshToken")
            else:
                raise Exception(f"Login failed with status code: {response.status_code}")
                
        except Exception as e:
            sys.exit("Exiting the program due to login failure.")

    # GeminiAI cleint
    def initialize_GeminiAI_client(self):
        if self.GeminiAI_api_key:
            self.GeminiAIclient = genai.Client(api_key=self.GeminiAI_api_key)
        else:
            sys.exit("Gemini API key not found. Please set the GEMINI_API_KEY environment variable.")
    
    # OpenAI cleint
    def initialize_OpenAI_client(self):
        if self.OpenAI_api_key:
            self.OpenAIclient = OpenAI(api_key=self.OpenAI_api_key)
        else:
            sys.exit("Gemini API key not found. Please set the GEMINI_API_KEY environment variable.")

    # select random address from the list of addresses.
    def selectAddress(self):
        locationInfo = random.choice(botLocationInfo)
        self.locationInfo = locationInfo

    # method to get a random prompt from the templates.
    def selectPrompt(self):
        topic = random.choice(list(templates.keys()))
        prompt = random.choice(templates[topic]).format(address=self.locationInfo.get("address"), society=self.locationInfo.get("society"), landmark=self.locationInfo.get("landmark"), city=self.locationInfo.get("city"))
        return prompt

    def generatePostByOpenAI(self, prompt):
        try:
            # Check if the OpenAI client is initialized, if not, initialize it.
            if not self.OpenAIclient:
                self.initialize_OpenAI_client()

            response = self.OpenAIclient.chat.completions.create(
                model="gpt-4",
                messages=[{
                    "role": "user", 
                    "content":f"""{prompt}
                        
                    Generate a response formatted as a JSON object adhering to the following structure.
                    The JSON object must contain:
                        - "type": A string, either "post" or "poll".
                        - "title": A string representing the title of the post or poll.
                        - "body": A string containing the text of the post or the poll question.
                        - "options": An array of strings representing the poll options (only required if type is "poll", can be an empty array if type is "post").
                    
                    Example for a post:
                    post  = {{
                    "type": "post",
                    "title": "Exciting News!",
                    "body": "Just launched our new product! Check it out.",
                    "options": []
                    }}

                    Example for a poll:
                    post = {{
                    "type": "poll",
                    "title": "Favorite Season",
                    "body": "What's your favorite season?",
                    "options": ["Spring", "Summer", "Autumn", "Winter"]
                    }}
                    """}],
                temperature=float(os.getenv("TEMPERATURE")),
            ) 
            post = json.loads(response.choices[0].message.content)
            return post

        except Exception as e:
            bot.unsuccessfulAttempts += 1
            print(f"Error generating post: {e}")
            return None

    # method through which Bot interacts with OpenAI API.
    def generatePostByGeminiAI(self, prompt):
        try:
            if not self.GeminiAIclient:
                self.initialize_GeminiAI_client()

            response = self.GeminiAIclient.models.generate_content(
                model = "gemini-2.0-flash",
                config = types.GenerateContentConfig(
                    temperature = float(os.getenv("TEMPERATURE")),
                    system_instruction="Act as a Post genertor Bot.Don't use words like 'Okay', 'Here is your post', etc.",
                    response_mime_type = "application/json",
                ),
                contents = f"""{prompt}
                    
                Generate a response formatted as a JSON object adhering to the following structure.
                The JSON object must contain:
                    - "type": A string, either "post" or "poll".
                    - "title": A string representing the title of the post or poll.
                    - "body": A string containing the text of the post or the poll question.
                    - "options": An array of strings representing the poll options (only required if type is "poll", can be an empty array if type is "post").
                
                Example for a post:
                post  = {{
                "type": "post",
                "title": "Exciting News!",
                "body": "Just launched our new product! Check it out.",
                "options": []
                }}

                Example for a poll:
                post = {{
                "type": "poll",
                "title": "Favorite Season",
                "body": "What's your favorite season?",
                "options": ["Spring", "Summer", "Autumn", "Winter"]
                }}
                """
            )
            post = json.loads(response.text)
            return post
        except Exception as e:
            bot.unsuccessfulAttempts += 1
            print(f"Error generating post: {e}")
            return None
    
    def savePost(self, post):   
        try:
            url = os.getenv("BASE_URL") + os.getenv("CREATE_POST_ENDPOINT")

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.accessToken}",
            }

            payload = {
                "title" : post.get("title"),
                "content" : post.get("body"),
                "type" : post.get("type"),
                "poll_options" : [{"option" : option , "optionId" : idx + 1} for idx, option in enumerate(post.get("options"))],
                "allowMultipleVotes" : False,
                "city" : self.locationInfo.get("city"),
                "location" : self.locationInfo.get("location"),
            }

            cookies = {
                'refreshToken': self.refreshToken
            }

            response = requests.post(url, data = payload, cookies = cookies)

            if response.status_code == 200:
                result = response.json()
                bot.postCreated += 1
                print("Post Created with contentid = ",result.get("contentid"))

            else:
                raise Exception(f"Post save failed with status code: {response.status_code}")

        except Exception as e:
            print(f"Error saving post: {e}")
            bot.unsuccessfulAttempts += 1
        
        finally:
            self.refreshToken = None
            self.accessToken = None
            self.locationInfo = None


if __name__ == "__main__":
    bot = PostBot()
    postCreated = 0
    unsuccessfulAttempts = 0
    SeedPostNeeded = random.randint(1, 15)

    for i in range(SeedPostNeeded):
        bot.login()
        bot.selectAddress()
        prompt = bot.selectPrompt()
        post = None
        if os.getenv("TO_USE") == "OpenAI":
            post = bot.generatePostByOpenAI(prompt)
        else:
            post = bot.generatePostByGeminiAI(prompt)
        if post:
            bot.savePost(post)

    print(f"Total Posts Created = {bot.postCreated}")
    print(f"Unsuccessful Attempts = {bot.unsuccessfulAttempts}")

    del bot


