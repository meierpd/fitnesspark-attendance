PROJECT_ID=fitnesspark-attendance
REGION=europe-west6
IMAGE=europe-west6-docker.pkg.dev/${PROJECT_ID}/fitnesspark-attendance/visualizer:latest
SERVICE=fitnesspark-visualizer

deploy:
	gcloud builds submit --tag $(IMAGE)
	gcloud run deploy $(SERVICE) \
		--image $(IMAGE) \
		--region $(REGION) \
		--allow-unauthenticated