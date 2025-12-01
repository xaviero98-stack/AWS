# Stock price forecasting

This is the overall arquitecture:

![My Image](Arquitecture%20schema.png)

In this lab we ingest historical stock data, train a predictive model, and save the resulting predictions to a data lake for use by stock analysts. We will assume the role of a Data scientist and load and run an Amazon SageMaker notebook application to obtain historical stock data and save it to a data lake in Amazon Simple Storage Service (Amazon S3). The SageMaker notebook calls TensorFlow on AWS to train a long short- term memory (LSTM) predictive model and other traditional ML models, using the historical stock data, and then saves prediction data to the S3 data lake. AWS Glue accesses s3 and discovers the prediction data's schema, which is used to create tables in the AWS Glue Data Catalog. Stock analysts access the saved prediction data by running SQL queries through Amazon Athena.

# S3

The substantial part of this lab takes place of the SageMaker Studio notebook but first we have to incorporate the used bucket on the script. For that we simply copy the bucket name on the S3 menu. 

![My Image](Captura%20de%20pantalla%202025-07-05%20105745.png)

# SageMaker Studio

After copying the bucket's name we navigate to the SageMaker AI and use the SageMaker Studio instance named **default-...**, this is an IDE with various notebook frameworks available within it like Jupyter Lab, the one we will use. We click on Jupyter Lab and click on the "run" button.

![My Image](Captura%20de%20pantalla%202025-07-05%20105908.png)

Once it lets us in we do so and select the python kernel. Then we will be inside the Jupyter Lab UI. Within it, we will see all the files available from the Jupyter Lab environment, we have to open the **stock_price_forecast.ipynb**.

![My Image](Captura%20de%20pantalla%202025-07-05%20110208.png)

# Jupyter Lab notebook

Now let's take a look a the notebook but first here is a guideline of the different stages we find in the script that, together, help serve as a general view of the purpose of the notebook and how each stage contributes in accomplishing it:

- **Stage 1:** We install and import all necessary python libraries. This encompasses cells 1 to 3.
- **Stage 2:** Then data is drawn from the S3 bucket, we seggregate it by firm, scale it with a MinMaxScaler and split it into test and training data. Finally, once data is formatted, we save it on S3 again so that we can access it from for training the LSTM model later. That part encompasses cells 4 to 15.
- **Stage 3**: Then, before training the LSTM we will also train a Random Forest algorithm so that its results get compared to the LSTM output. Random Forest estimations will act as a baseline to know how LSTM performs. The exact steps are gathering the test and train data for the JAJIL.CQ firm (the only firm we will predict), do some feature enginnering to create a moving average, and some delayed versions of the adjclose price (the target variable) with different backward shifts, and then resplit them again into train and test to fit the model using this data. To conclude, we compute the RMSE (RootSquaredMeanError) and MAE (MeanAbsoluteError) to finally make a line chart with both real and predicted prices for the test data and see how much resemblant they are. This is done in cells 16 to 26.
- **Stage 4**: Here is we train the LSTM model. This model is the main model here and will be trained leveraging AWS cloud power and infrastructure but ehich requieres its own procedures different from training a machine learning algorithm like the Random Forest on a local environment. We will start by creating the TensorFlow job in which we specify things like the TensorFlow or Pyhton versions to use, the AWS hardware, in my case the ml.m5.large instance, the Python script to incorporate inside the image put in the AWS instance, the number of instances you want to use or environment variables on the instance/s, among others. In our case we will use only one machine but if we wanted we could have a distributed traning increasing the name of the instance_count variable and making some adjustments on the train.py code we pass to the instances to make them aware that they have to distribute the training among each other. Otherwise, we will be training the same model as many times as the count of the machines we use. The script itself has nothing more than the Python code which, in turn, uses the TensorFlow library to create the LSTM architecture, draw the data we saved on S3 in Stage 2, shape it so that it can be passed as input to the LSTM model and train the model. Then the trained model is stored in S3. This is done in cells 27 to 31.

  The exact train.py script is stored in this repository and also has expanded comments so that we can get an accurate perception of what it does:

  **train.py:** [train.py](train.py)
  
- **Stage 5:** First of all, this LSTM trained model trascends the scope of the Jupyter Lab environment as opposed to the Random Forest case where the model is hold on the memory of the machine running the Jupyter Lab notebook. It happens because models trained using the a SageMaker job use temporal instances (such as the ml.m5.xlarge instace in my case as mentioned before) so SageMaker and S3 stores the resulting trained model for further use. Now we can create an endpoint that will make inferences when we pass input data to it because it hosts our trained model. This endpoint is an object that gets created inside the SageMaker environment and appears listed on the endpoint tab on the AWS console it also requires AWS infrastructure (intances) to make the inferences and is scalable in case we need predictions over large amounts of input data. Once created, we re-instantiate it to configure a JSON serializer so it returns predictions as a JSON and then use the test data for the LSTM and shape it to be valid to the input requirements for the inference endpoint. Inference data needs to have the exact same shape as the training data used, that's why this transformation process is the exact same we use on the _transform_data function in the train.py script. After obtaining the predictions, we unscale them and we also use RSME and MAE to compare real prices to unscaled predictions. Finally we can make a graph to see how much alike the prediction and real prices are when plotted. This process in made in cells 32 to 43.

  We can see the endpoint here:

  ![MY IMAGE](Captura%20de%20pantalla%202025-07-05%20111615.png)

- **Stage 6**: Once we have it all we can save the dataframe of real prices and predictions as a parquet file inside S3.

  

📓 **Notebook:** [stock_price_forecast.ipynb](stock_price_forecast.ipynb)

# Register the tables in the Glue catalog 

Now we have to create a database:

![MY IMAGE](Captura%20de%20pantalla%202025-07-05%20112410.png)

But since the database will empty:

![MY IMAGE](Captura%20de%20pantalla%202025-07-05%20112455.png)

# Create a crawler to scan S3 files

We need to also add a crawler to scan the S3 data with predicitions and prices which will, in turn, create the table in the database with that hosts the metadata gathered by the crawler, here are shown the steps and exact confs for the crawler:

![MY IMAGE](Captura%20de%20pantalla%202025-07-05%20112551.png)

![MY IMAGE](Captura%20de%20pantalla%202025-07-05%20112740.png)

![MY IMAGE](Captura%20de%20pantalla%202025-07-05%20112714.png)

![MY IMAGE](Captura%20de%20pantalla%202025-07-05%20112838.png)

![MY IMAGE](Captura%20de%20pantalla%202025-07-05%20112928.png)

![MY IMAGE](Captura%20de%20pantalla%202025-07-05%20113311.png)

When we have our crawler created we just have to run it and wait for the scanning to complete:

![MY IMAGE](Captura%20de%20pantalla%202025-07-05%20113812.png)


# Query data from Athena (Trino)

Now we navigate to Athena and we can start querying the results 

![MY IMAGE](Captura%20de%20pantalla%202025-07-05%20114302.png)


# Disclamer:

The code used here was given to me as a lab resource and all of the techniques and procedures where not crafted by me. However, I thought it was an amazing opportunity to carefully explain and review all the things we code did adding or expanding on commentaries already present in the script and, therefore understanding how the Jupyter Lab and the train.py script interacted with the different AWS resources to build up a complete example of an MLOps pipeline in AWS.
