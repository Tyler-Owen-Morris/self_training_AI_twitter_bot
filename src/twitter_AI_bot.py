from tweepy import OAuthHandler, Cursor, API
import os
from random import choice
import gpt_2_simple as gpt2
import twitter_credentials as tc

auth = OAuthHandler(tc.CONSUMER_KEY, tc.CONSUMER_SECRET)
auth.set_access_token(tc.ACCESS_TOKEN, tc.ACCESS_TOKEN_SECRET)
api = API(auth, wait_on_rate_limit=True, wait_on_rate_limit_notify=True)

model_name = "355M"
if not os.path.isdir(os.path.join("models", model_name)):
    print(f"Downloading {model_name} model...")
    gpt2.download_gpt2(model_name=model_name)


def get_trending():
    trends = api.trends_place(id=23424977)
    trending = []
    for trend in trends[0]["trends"]:
        trending.append(trend["name"])
    return trending


def get_topic_tweet(topic, max_tweets=100):
    searched_tweets = [
        status
        for status in Cursor(
            api.search, q=topic + " -filter:retweets", lang="en", tweet_mode="extended"
        ).items(max_tweets)
    ]
    found_tweets = []
    for tweet in searched_tweets:
        try:
            found_tweets.append(tweet.full_text)
        except:
            pass
    return found_tweets


def generate_trending_tweet():
    # pick a topic
    trending = get_trending()
    topic = choice(trending)
    print("generating tweets on topic: " + topic)
    # fetch tweets on topic
    file_name = "../data/" + topic + ".txt"
    topical_tweets = get_topic_tweet(topic, 1000)
    tweet_string = " || ".join(topical_tweets)
    with open(file_name, "w") as f:
        f.write(tweet_string)
    # train a model on new tweets
    sess = gpt2.start_tf_sess()
    if not os.path.exists("checkpoint/" + topic):
        gpt2.finetune(
            sess,
            dataset=file_name,
            model_name=model_name,
            steps=2,
            restore_from="fresh",
            run_name=topic,
            print_every=1,
        )
    else:
        gpt2.finetune(
            sess,
            dataset=file_name,
            model_name=model_name,
            steps=1,
            restore_from="latest",
            run_name=topic,
            print_every=1,
        )
    # generate text with the new model
    gpt2.generate_to_file(
        sess,
        length=400,
        destination_path="../data/generated_tweets.txt",
        nsamples=5,
        run_name=topic,
        prefix=topic,
    )
    gpt2.reset_session(sess)
    # filter and return 1 valid tweet from the gerated text
    with open("../data/generated_tweets.txt", "r") as f:
        texts = f.read().split("====================")
    tweets = []
    for text in texts:
        tweeters = text.split(" || ")
        for tweet in tweeters:
            if topic in tweet:
                tweet = tweet.split(" ")
                tweet = " ".join(word for word in tweet if not filter_links(word))
                if len(tweet) > len(topic) + 4:
                    tweets.append(tweet)
            else:
                continue
    tweet = choice(tweets)
    if len(tweet) > 280:
        tweet = tweet[:280]
    return tweet


def filter_links(word):
    if word.find("http") != -1:
        return True
    return False


def run_bot():
    while True:
        tweet = generate_trending_tweet()
        print("I am tweeting: " + tweet)
        api.update_status(tweet)


if __name__ == "__main__":
    run_bot()
