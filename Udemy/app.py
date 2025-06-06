import os
from flask import Flask, request, render_template

import pandas as pd
import numpy as np
import neattext.functions as nfx
from sklearn.feature_extraction.text import TfidfVectorizer, CountVectorizer
from sklearn.metrics.pairwise import cosine_similarity


app = Flask(__name__)


def getcosinemat(df):

    countvect = CountVectorizer()
    cvmat = countvect.fit_transform(df['Clean_title'])
    return cvmat

# getting the title which doesn't contain stopwords and all which we removed with the help of nfx


def getcleantitle(df):

    df['Clean_title'] = df['course_title'].apply(nfx.remove_stopwords)

    df['Clean_title'] = df['Clean_title'].apply(nfx.remove_special_characters)

    return df


def cosinesimmat(cv_mat):

    return cosine_similarity(cv_mat)


def readdata():
    
    os.chdir('C:/Users/mohit/Desktop/Codes/Udemy')

    # Try to read the file from the current directory
    try:
        df = pd.read_csv('UdemyCleanedTitle.csv')
        return df
    except FileNotFoundError as e:
        print(f"Error: {e}")

# this is the main recommendation logic for a particular title which is choosen


'''def recommend_course(df, title, cosine_mat, numrec):

    course_index = pd.Series(
        df.index, index=df['course_title']).drop_duplicates()

    index = course_index[title]

    scores = list(enumerate(cosine_mat[index]))

    sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)

    selected_course_index = [i[0] for i in sorted_scores[1:]]

    selected_course_score = [i[1] for i in sorted_scores[1:]]

    rec_df = df.iloc[selected_course_index]

    rec_df['Similarity_Score'] = selected_course_score

    final_recommended_courses = rec_df[[
        'course_title', 'Similarity_Score', 'url', 'price', 'num_subscribers']]

    return final_recommended_courses.head(numrec)

# this will be called when a part of the title is used,not the complete title!


def searchterm(term, df):
    result_df = df[df['course_title'].str.contains(term)]
    top6 = result_df.sort_values(by='num_subscribers', ascending=False).head(6)
    return top6'''

import pandas as pd

def recommend_course(df, title, cosine_mat, numrec):
    # Convert course titles to lowercase to ensure case-insensitivity
    course_index = pd.Series(
        df.index, index=df['course_title'].str.lower()).drop_duplicates()

    # Convert the input title to lowercase
    title_lower = title.lower()

    # Check if the title exists in the course index
    if title_lower not in course_index:
        print(f"Course with title '{title}' not found!")
        return None

    # Get the index of the chosen course using the lowercase title
    index = course_index[title_lower]

    # Get the cosine similarity scores for the chosen course
    scores = list(enumerate(cosine_mat[index]))

    # Sort the scores in descending order
    sorted_scores = sorted(scores, key=lambda x: x[1], reverse=True)

    # Select the courses with the highest similarity scores (excluding the chosen course)
    selected_course_index = [i[0] for i in sorted_scores[1:]]
    selected_course_score = [i[1] for i in sorted_scores[1:]]

    # Get the recommended courses
    rec_df = df.iloc[selected_course_index]
    rec_df['Similarity_Score'] = selected_course_score

    # Return the final recommended courses with necessary columns
    final_recommended_courses = rec_df[['course_title', 'Similarity_Score', 'url', 'price', 'num_subscribers']]

    return final_recommended_courses.head(numrec)


def searchterm(term, df):
    # Convert the search term and course titles to lowercase to ensure case-insensitivity
    result_df = df[df['course_title'].str.contains(term.lower(), case=False)]
    
    # Sort by number of subscribers and return top 6 results
    top6 = result_df.sort_values(by='num_subscribers', ascending=False).head(6)
    return top6

# extract features from the recommended dataframe

def extractfeatures(recdf):

    course_url = list(recdf['url'])
    course_title = list(recdf['course_title'])
    course_price = list(recdf['price'])

    return course_url, course_title, course_price


@app.route('/', methods=['GET', 'POST'])
def hello_world():

    if request.method == 'POST':
        df = readdata()
        my_dict = request.form
        titlename = my_dict['course']
        print(titlename)
        try:
            df = readdata()
            df = getcleantitle(df)
            cvmat = getcosinemat(df)

            num_rec = 6
            cosine_mat = cosinesimmat(cvmat)

            recdf = recommend_course(df, titlename,
                                     cosine_mat, num_rec)

            course_url, course_title, course_price = extractfeatures(recdf)

            # print(len(extractimages(course_url[1])))

            dictmap = dict(zip(course_title, course_url))

            if len(dictmap) != 0:
                return render_template('index.html', coursemap=dictmap, coursename=titlename, showtitle=True)

            else:
                return render_template('index.html', showerror=True, coursename=titlename)

        except:

            resultdf = searchterm(titlename, df)
            if resultdf.shape[0] > 6:
                resultdf = resultdf.head(6)
                course_url, course_title, course_price = extractfeatures(
                    resultdf)
                coursemap = dict(zip(course_title, course_url))
                if len(coursemap) != 0:
                    return render_template('index.html', coursemap=coursemap, coursename=titlename, showtitle=True)

                else:
                    return render_template('index.html', showerror=True, coursename=titlename)

            else:
                course_url, course_title, course_price = extractfeatures(
                    resultdf)
                coursemap = dict(zip(course_title, course_url))
                if len(coursemap) != 0:
                    return render_template('index.html', coursemap=coursemap, coursename=titlename, showtitle=True)

                else:
                    return render_template('index.html', showerror=True, coursename=titlename)

    return render_template('index.html')


if __name__ == '__main__':
    app.run(debug=True)
