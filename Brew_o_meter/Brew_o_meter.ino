int light = A1;
int temp_amb = A0;
int pres_beer = A3;
int temp_beer = 10;
int buzzer = 8;

void setup() {
    digitalWrite(temp_beer, LOW);
    pinMode(temp_beer, INPUT);
    pinMode(buzzer, OUTPUT);
    Serial.begin(9600);
}

void loop() {
  int req = Serial.read();
  if(req == 66) {
    tone(buzzer, 440);
    delay(200);
    tone(buzzer, 0 );
  };
  if(req == 82) {    
    float light_val = analogRead(light);
    float temp_amb_val = 1.8*(analogRead(temp_amb)*5000.0/1024.0 - 500.0)/10.0 + 32.0;
    float pres_beer_val = analogRead(pres_beer);
    float temp_beer_val = 1.8*tempC(temp_beer) + 32.0;
    
    float chk_sum = light_val + temp_amb_val + temp_beer_val + pres_beer_val;
    
    Serial.print("{");
    
    Serial.print("'chk_sum':");
    Serial.print(chk_sum);
    
    Serial.print(", 'light_amb':");
    Serial.print(light_val);
    
    Serial.print(", 'temp_amb':");
    Serial.print(temp_amb_val);
    
    Serial.print(", 'temp_beer':");
    Serial.print(temp_beer_val);
    
    Serial.print(", 'pres_beer':");
    Serial.print(pres_beer_val);
    
    Serial.println("}");
  } else if(req == 69) {
    Serial.println("Established");
  }
}

float tempC(int TEMP_PIN) {
  int HighByte, LowByte, TReading, SignBit, Tc_100, Whole, Fract;

  OneWireReset(TEMP_PIN);
  OneWireOutByte(TEMP_PIN, 0xcc);
  OneWireOutByte(TEMP_PIN, 0x44); // perform temperature conversion, strong pullup for one sec

  OneWireReset(TEMP_PIN);
  OneWireOutByte(TEMP_PIN, 0xcc);
  OneWireOutByte(TEMP_PIN, 0xbe);

  LowByte = OneWireInByte(TEMP_PIN);
  HighByte = OneWireInByte(TEMP_PIN);
  TReading = (HighByte << 8) + LowByte;
  SignBit = TReading & 0x8000;  // test most sig bit
  if (SignBit) // negative
  {
    TReading = (TReading ^ 0xffff) + 1; // 2's comp
  }
  Tc_100 = (6 * TReading) + TReading / 4;    // multiply by (100 * 0.0625) or 6.25

  Whole = Tc_100 / 100;  // separate off the whole and fractional portions
  Fract = Tc_100 % 100;

  String out = "";
  if (SignBit) // If its negative
  {
     out += "-";
  }
  out += Whole;
  out += ".";
  if (Fract < 10)
  {
     out += "0";
  }

  return(out.toFloat());
}

void OneWireReset(int Pin) // reset.  Should improve to act as a presence pulse
{
     digitalWrite(Pin, LOW);
     pinMode(Pin, OUTPUT); // bring low for 500 us
     delayMicroseconds(500);
     pinMode(Pin, INPUT);
     delayMicroseconds(500);
}

void OneWireOutByte(int Pin, byte d) // output byte d (least sig bit first).
{
   byte n;

   for(n=8; n!=0; n--)
   {
      if ((d & 0x01) == 1)  // test least sig bit
      {
         digitalWrite(Pin, LOW);
         pinMode(Pin, OUTPUT);
         delayMicroseconds(5);
         pinMode(Pin, INPUT);
         delayMicroseconds(60);
      }
      else
      {
         digitalWrite(Pin, LOW);
         pinMode(Pin, OUTPUT);
         delayMicroseconds(60);
         pinMode(Pin, INPUT);
      }

      d=d>>1; // now the next bit is in the least sig bit position.
   }

}

byte OneWireInByte(int Pin) // read byte, least sig byte first
{
    byte d, n, b;

    for (n=0; n<8; n++)
    {
        digitalWrite(Pin, LOW);
        pinMode(Pin, OUTPUT);
        delayMicroseconds(5);
        pinMode(Pin, INPUT);
        delayMicroseconds(5);
        b = digitalRead(Pin);
        delayMicroseconds(50);
        d = (d >> 1) | (b<<7); // shift d to right and insert b in most sig bit position
    }
    return(d);
}
