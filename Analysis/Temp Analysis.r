library(ggplot2)
library(plyr)
setwd("C:\\Users\\matr06619\\Documents\\Other\\MyProjects\\Brew-o-meter")

files <- list.files(path = "Logs", full.names = TRUE,
                    pattern = "(?i)SENSOR LoG [[:digit:]]{8}_[[:digit:]]{4}.csv")

if(exists("allLogs")) rm("allLogs")
for(file in files) {
  if(exists("allLogs")) allLogs <- rbind(allLogs, read.csv(file, stringsAsFactors = FALSE))
  else allLogs <- read.csv(file, stringsAsFactors = FALSE)
}
allLogs$Diff <- with(allLogs, temp_beer - temp_amb)

mean_diffs <- ddply(allLogs, "temp_beer", summarise,
                    mean_diff = mean(Diff),
                    min_diff = min(Diff),
                    max_diff = max(Diff),
                    count = length(Diff))
give.n <- function(x){
  out = c(y = mean(x), label = length(x))
  if(out["label"] <= 50) out["label"] <- NA
  return(out)
}
ggplot(allLogs, aes(as.factor(temp_beer), Diff)) + 
  geom_boxplot() + 
  stat_summary(fun.data = give.n, geom = "text")
boxplot(allLogs$Diff~allLogs$temp_beer)
plot(mean_diffs$count~mean_diffs$temp_beer, type = "h")

mean_diffs <- ddply(allLogs, "temp_amb", summarise,
                    mean_diff = mean(Diff),
                    min_diff = min(Diff),
                    max_diff = max(Diff),
                    count = length(Diff))
plot(mean_diffs$count~mean_diffs$temp_amb, type = "h")
mean(allLogs$Diff)
