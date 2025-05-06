import os, sys, json, random, requests
from openai import OpenAI
from dotenv import load_dotenv
from constants import botLocationInfo

class CommentBot:
    def __init__(self):
        load_dotenv(dotenv_path="./config.env")
        self.OpenAI_api_key = os.getenv("OPENAI_API_KEY")
        self.locationInfo = None
        self.OpenAIclient = None
        self.accessToken = None
        self.refreshToken = None
        self.successfullComments = []
        self.unsuccessfulComments = []

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

            url = os.getenv("LOCAL_URL") + os.getenv("LOGIN_ENDPOINT")
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

    def fetchPosts(self):
        try:
            url = os.getenv("LOCAL_URL") + os.getenv("FETCH_POST_ENDPOINT")
            headers = {
                "Content-Type": "application/json",
            } 

            response = requests.get(url, headers = headers)

            if response.status_code == 200:
                posts = response.json().get("posts")
                return posts
            else:
                raise Exception(f"Fetch post failed with status code: {response.status_code}")

        except Exception as e:
            sys.exit("Exiting the program due to fetch posts failure.")

    def genearteComment(self, post):
        try:
            # Check if the OpenAI client is initialized, if not, initialize it.
            if not self.OpenAIclient:
                self.initialize_OpenAI_client()
            
            society = self.locationInfo.get("society")
            address = self.locationInfo.get("address")
            city = self.locationInfo.get("city")
            location = self.locationInfo.get("location")
            landmark = self.locationInfo.get("landmark")
            
            response = self.OpenAIclient.chat.completions.create(
                model="gpt-4",
                messages = [{
                    "role" : "user",
                    "content" : f""" 
                        Consider yourself a person of a randome age older than 18 years. You live in {society},{address},{city} near {landmark} and 
                        your co-ordinates are {location}.

                        You are using a social media app and watching a post that can be a post or poll.
                        Post is : {post}.

                        Now you want to comment that post/poll.
                        Generate comment like a human by being respectfully but you can pick moods of human randomly to give comment.
                        It is not neccessary to be formal you can even comment causally, it will be good if you comment in Indian style.
                        Try to avoid starting like Hi, Hey, Hello, etc. or addressing author.
                    """
                }],
                temperature=float(os.getenv("TEMPERATURE")),
            )

            comment = response.choices[0].message.content
            return comment

        except Exception as e:
            self.unsuccessfulComments.append({ "contentid" : post.get("contentid"), "errorMessage" : str(e) })
            print(f"Error generating comment: {e}")
            return None

    def saveComment(self, contentid, comment):
        try:
            url = os.getenv("LOCAL_URL") + os.getenv("CREATE_COMMENT_ENDPOINT")

            headers = {
                "Content-Type" : "application/json",
                "Authorization" : "Bearer {self.accessToken}"
            }

            cookies = {
                "refreshToken" : self.refreshToken
            }

            payload = {
                'contentid' : contentid,
                'text' : comment
            }

            response = requests.post(url, headers = headers, cookies = cookies, json = payload)

            if response.status_code == 201:
                result = response.json()
                commentid = result.get("commentid")
                self.successfullComments.append({ "contentid" : post.get("contentid"), "commentid" : commentid, "successMessage" : "Comment created Successfully." })
            else:
                raise Exception(f"saving comment failed with status code: {response.status_code}")

        except Exception as e:
            self.unsuccessfulComments.append({ "contentid" : post.get("contentid"), "errorMessage" : str(e) })

        finally:
            self.refreshToken = None
            self.accessToken = None
            self.locationInfo = None


if __name__ == '__main__':
    load_dotenv()
    bot = CommentBot()
    posts = bot.fetchPosts()
    for post in posts:
        bot.login()
        bot.selectAddress()
        comment = bot.genearteComment(post)
        bot.saveComment(post.get("contentid"), comment)
    print("Successfull comments created by bot :")
    for entry in bot.successfullComments:
        print(entry)
    
    print("Unsuccessfull comments creation attempt by bot :")
    for entry in bot.unsuccessfulComments:
        print(entry)
    del bot
