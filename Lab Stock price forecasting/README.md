# Stock price forecasting

This is the overall arquitecture:

![My Image](Arquitecture%20schema.png)

In this lab we ingest historical stock data, train a predictive model, and save the resulting predictions to a data lake for use by stock analysts. We will assume the role of a Data scientist and load and run an Amazon SageMaker notebook application to obtain historical stock data and save it to a data lake in Amazon Simple Storage Service (Amazon S3). The SageMaker notebook calls TensorFlow on AWS to train a long short- term memory (LSTM) predictive model and other tradirional ML models, using the historical stock data, and then saves prediction data to the S3 data lake. AWS Glue accesses the data lake and discovers the prediction data's schema, which is used to create tables in the AWS Glue Data Catalog. Stock analysts access the saved prediction data by running SQL queries through Amazon Athena. The analysts use a dashboard or visualization application that imports the query results from Athena.

# S3

The substantial part of this lab takes place of the SageMaker Studio notebook but first we have to incorporate the used bucket on the script. For that we simply copy the bucket name on the S3 menu. 

![My Image](Captura%20de%20pantalla%202025-07-05%20105745.png)

# SageMaker Studio

After copying the bucket's name we navigate to the SageMaker AI and use the SageMaker Studio instance named **default-...**, this is an IDE with various notebook frameworks available within it like Jupyter Lab, the we will use. We click on Jupyter Lab and click on the "run" button.

![My Image](Captura%20de%20pantalla%202025-07-05%20105908.png)

Once it lets us in we do so and select the python kernel. Then we will be inside the Jupyter Lab UI. we will also see all the files available from the Juoyter Lab environment, we have to open the **stock_price_forecast.ipynb**.

![My Image](Captura%20de%20pantalla%202025-07-05%20110208.png)

# Jupyter Lab notebook

Now let's take a look a the notebook but first here is a guideline of the different satges we find in the script that serves as a general view of the purpose each stage accomplishes and how they are connected:

- **Stage 1:** We install and import all necessary python libraries, this encompasses cells 1 to 3.
- **Stage 2:** Then data is drawn from the S3 bucket, we seggregate it by firm, scale it with a MinMaxScaler and split it into test and training data. Finally, once well formatted we save it on S3 again so that we can access it from for training the LSTM later.
- **Stage 3**:   


📓 **Notebook:** [stock_price_forecast.ipynb](stock_price_forecast.ipynb)
