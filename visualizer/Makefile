PROJECT_ID=fitnesspark-attendance
REGION=europe-west6
SERVICE=fitnesspark-visualizer
IMAGE=europe-west6-docker.pkg.dev/${PROJECT_ID}/fitnesspark-attendance/visualizer:latest

deploy:
	gcloud builds submit --project $(PROJECT_ID) --tag $(IMAGE)
	gcloud run deploy $(SERVICE) \
		--project $(PROJECT_ID) \
		--image $(IMAGE) \
		--region $(REGION) \
		--allow-unauthenticated

teardown:
	gcloud run services delete $(SERVICE) \
		--project $(PROJECT_ID) \
		--region $(REGION) \
		--quiet
	gcloud artifacts docker images delete $(IMAGE) \
		--project $(PROJECT_ID) \
		--quiet || true