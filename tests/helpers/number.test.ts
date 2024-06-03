import { presentNumber, presentPercentage } from "../../app/helpers/number";

describe("presentNumber", () => {
  describe("when the digits are 2", () => {
    const digits = 2;

    describe("when the value is null", () => {
      const value = null;

      it("is 'NA'", () => {
        const presentedNumber = presentNumber(value, digits);
        expect(presentedNumber).toEqual("NA");
      });
    });

    describe("when the value is 0.00", () => {
      const value = 0;

      it("is '0'", () => {
        const presentedNumber = presentNumber(value, digits);
        expect(presentedNumber).toEqual("0.00");
      });
    });

    describe("when the value is positive", () => {
      const value = 5.1298;

      it("is rounded to 2 digits", () => {
        const presentedNumber = presentNumber(value, digits);
        expect(presentedNumber).toEqual("5.13");
      });
    });

    describe("when the value is negative", () => {
      const value = -5.1298;

      it("includes the negative sign", () => {
        const presentedNumber = presentNumber(value, digits);
        expect(presentedNumber).toEqual("-5.13");
      });
    });
  });

  describe("when the digits are undefined", () => {
    const value = 5.1298;

    it("doesn't include digits", () => {
      const presentedNumber = presentNumber(value);
      expect(presentedNumber).toEqual("5");
    });
  });
});

describe("presentPercentage", () => {
  describe("when the value is null", () => {
    const value = null;

    it("is 'NA'", () => {
      const presentedNumber = presentPercentage(value);
      expect(presentedNumber).toEqual("NA");
    });
  });

  describe("when the value is 0.00", () => {
    const value = 0;

    it("is '0'", () => {
      const presentedNumber = presentPercentage(value);
      expect(presentedNumber).toEqual("0.00%");
    });
  });

  describe("when the value is positive", () => {
    const value = 5.1298;

    it("is rounded to 2 digits", () => {
      const presentedNumber = presentPercentage(value);
      expect(presentedNumber).toEqual("512.98%");
    });
  });

  describe("when the value is negative", () => {
    const value = -5.1298;

    it("includes the negative sign", () => {
      const presentedNumber = presentPercentage(value);
      expect(presentedNumber).toEqual("-512.98%");
    });
  });
});
